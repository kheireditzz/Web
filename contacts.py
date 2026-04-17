"""
Contact management — load, validate, and manage recipients from CSV.

Expected CSV columns:
  phone      (required) — E.164 format, e.g. 628123456789
  name       (optional) — used as {{1}} variable in templates
  Any extra columns are available as template variables.

Example CSV:
  phone,name,promo_code
  628123456789,Andi,SAVE20
  6281234567890,Budi,SAVE30
"""

import csv
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

E164_RE = re.compile(r"^\d{7,15}$")  # digits only, no + prefix for Meta API


@dataclass
class Contact:
    phone: str
    name: str = ""
    variables: dict = field(default_factory=dict)


def load_contacts(path: str) -> list[Contact]:
    """Load and validate contacts from a CSV file."""
    contacts: list[Contact] = []
    skipped = 0
    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(f"Contacts file not found: {path}")

    with p.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if "phone" not in (reader.fieldnames or []):
            raise ValueError("CSV must have a 'phone' column")

        for i, row in enumerate(reader, start=2):  # row 1 = header
            raw_phone = row.pop("phone", "").strip().lstrip("+")
            name = row.pop("name", "").strip()

            if not E164_RE.match(raw_phone):
                logger.warning("Row %d: invalid phone '%s' — skipped", i, raw_phone)
                skipped += 1
                continue

            contacts.append(Contact(phone=raw_phone, name=name, variables=dict(row)))

    logger.info(
        "Loaded %d contacts from %s (%d skipped)",
        len(contacts),
        path,
        skipped,
    )
    return contacts


def render_message(template: str, contact: Contact) -> str:
    """
    Replace {{name}}, {{phone}}, and any custom column placeholders.
    e.g. "Hi {{name}}, use code {{promo_code}}" → "Hi Andi, use code SAVE20"
    """
    ctx = {"name": contact.name, "phone": contact.phone, **contact.variables}
    for key, val in ctx.items():
        template = template.replace("{{" + key + "}}", val)
    return template
