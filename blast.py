"""
Blast engine — sends messages to a list of contacts with rate limiting,
retry logic, and a per-run CSV report.
"""

import csv
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from client import WhatsAppClient
from contacts import Contact, render_message

logger = logging.getLogger(__name__)

# Meta Cloud API: 80 messages/sec on tier 1 — stay well under it
DEFAULT_DELAY_SECONDS = 1.0
DEFAULT_MAX_RETRIES = 2


class BlastResult:
    def __init__(self):
        self.sent: list[dict] = []
        self.failed: list[dict] = []
        self.start_time = datetime.now()

    @property
    def total(self):
        return len(self.sent) + len(self.failed)

    def summary(self) -> str:
        duration = (datetime.now() - self.start_time).total_seconds()
        return (
            f"\n{'='*40}\n"
            f"  Blast complete\n"
            f"  Sent:   {len(self.sent)}/{self.total}\n"
            f"  Failed: {len(self.failed)}/{self.total}\n"
            f"  Time:   {duration:.1f}s\n"
            f"{'='*40}"
        )

    def save_report(self, output_dir: str = ".") -> str:
        ts = self.start_time.strftime("%Y%m%d_%H%M%S")
        path = Path(output_dir) / f"blast_report_{ts}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["phone", "name", "status", "message_id", "error"]
            )
            writer.writeheader()
            for row in self.sent + self.failed:
                writer.writerow(row)
        logger.info("Report saved to %s", path)
        return str(path)


def send_blast(
    client: WhatsAppClient,
    contacts: list[Contact],
    *,
    # --- Text blast ---
    message_template: Optional[str] = None,
    # --- Template blast ---
    wa_template_name: Optional[str] = None,
    wa_template_language: str = "en_US",
    wa_template_body_vars: Optional[list[str]] = None,  # column names for {{1}},{{2}}…
    # --- Options ---
    delay: float = DEFAULT_DELAY_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    dry_run: bool = False,
    on_progress: Optional[Callable[[int, int, Contact, bool], None]] = None,
    output_dir: str = ".",
) -> BlastResult:
    """
    Send messages to all contacts.

    Use EITHER message_template (free-form text) OR wa_template_name (approved template).
    Free-form text only works within the 24-hour customer service window.
    Use approved templates for proactive/marketing blasts.
    """
    if not message_template and not wa_template_name:
        raise ValueError("Provide either message_template or wa_template_name")

    result = BlastResult()
    total = len(contacts)

    logger.info(
        "Starting blast → %d contacts | delay=%.1fs | dry_run=%s",
        total,
        delay,
        dry_run,
    )

    for idx, contact in enumerate(contacts, start=1):
        success = False
        error_msg = ""
        message_id = ""

        if dry_run:
            preview = (
                render_message(message_template, contact)
                if message_template
                else f"[template:{wa_template_name}]"
            )
            logger.info("[DRY RUN] %d/%d → %s | %s", idx, total, contact.phone, preview)
            success = True
        else:
            for attempt in range(1, max_retries + 2):
                try:
                    if message_template:
                        body = render_message(message_template, contact)
                        resp = client.send_text(contact.phone, body)
                    else:
                        components = _build_template_components(
                            contact, wa_template_body_vars or []
                        )
                        resp = client.send_template(
                            contact.phone,
                            wa_template_name,
                            wa_template_language,
                            components or None,
                        )

                    if resp["success"]:
                        message_id = (
                            resp.get("data", {})
                            .get("messages", [{}])[0]
                            .get("id", "")
                        )
                        success = True
                        break
                    else:
                        error_msg = resp.get("error", "unknown")
                        if attempt <= max_retries:
                            logger.warning(
                                "Retry %d/%d for %s: %s",
                                attempt,
                                max_retries,
                                contact.phone,
                                error_msg,
                            )
                            time.sleep(delay * attempt)
                except Exception as e:
                    error_msg = str(e)
                    logger.error("Exception for %s: %s", contact.phone, e)

        row = {
            "phone": contact.phone,
            "name": contact.name,
            "status": "sent" if success else "failed",
            "message_id": message_id,
            "error": error_msg,
        }
        (result.sent if success else result.failed).append(row)

        if on_progress:
            on_progress(idx, total, contact, success)

        if not dry_run and idx < total:
            time.sleep(delay)

    print(result.summary())
    result.save_report(output_dir)
    return result


def _build_template_components(contact: Contact, var_columns: list[str]) -> list:
    """Build template body component with positional variables."""
    if not var_columns:
        # Use name as {{1}} by default if no columns specified
        if contact.name:
            return [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": contact.name}],
                }
            ]
        return []

    params = []
    for col in var_columns:
        val = contact.variables.get(col, contact.name if col == "name" else "")
        params.append({"type": "text", "text": val})

    return [{"type": "body", "parameters": params}]
