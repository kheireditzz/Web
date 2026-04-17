#!/usr/bin/env python3
"""
WhatsApp Blast — CLI entry point.

Usage examples:

  # Text blast (free-form, within 24hr window)
  python main.py \
    --contacts contacts.csv \
    --message "Hi {{name}}, your promo code is {{promo_code}}. Valid today only!"

  # Template blast (approved template, works anytime)
  python main.py \
    --contacts contacts.csv \
    --template hello_world \
    --template-lang en_US \
    --template-vars name

  # Dry run (no messages sent — preview only)
  python main.py --contacts contacts.csv --message "Hi {{name}}!" --dry-run

Environment variables (or use a .env file):
  WA_PHONE_NUMBER_ID   — your WhatsApp Business phone number ID
  WA_ACCESS_TOKEN      — your Meta access token
"""

import argparse
import logging
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv optional

from client import WhatsAppClient
from contacts import load_contacts
from blast import send_blast

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def progress_bar(idx: int, total: int, contact, success: bool):
    symbol = "✓" if success else "✗"
    pct = int(idx / total * 40)
    bar = "#" * pct + "-" * (40 - pct)
    print(
        f"\r  {symbol} [{bar}] {idx}/{total} → {contact.phone}",
        end="",
        flush=True,
    )
    if idx == total:
        print()


def main():
    parser = argparse.ArgumentParser(
        description="WhatsApp Business API blast tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--contacts", required=True, help="Path to contacts CSV file")
    parser.add_argument(
        "--message",
        help='Free-form text template. Use {{name}}, {{column}} for substitution.',
    )
    parser.add_argument("--template", help="Approved WhatsApp template name")
    parser.add_argument(
        "--template-lang", default="en_US", help="Template language code (default: en_US)"
    )
    parser.add_argument(
        "--template-vars",
        nargs="*",
        help="CSV column names to use as template body variables (in order)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds between messages (default: 1.0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without actually sending messages",
    )
    parser.add_argument(
        "--output-dir", default=".", help="Directory for the report CSV (default: .)"
    )

    args = parser.parse_args()

    if not args.message and not args.template:
        parser.error("Provide either --message or --template")

    phone_number_id = os.getenv("WA_PHONE_NUMBER_ID")
    access_token = os.getenv("WA_ACCESS_TOKEN")

    if not phone_number_id or not access_token:
        logger.error(
            "Missing credentials. Set WA_PHONE_NUMBER_ID and WA_ACCESS_TOKEN "
            "as environment variables or in a .env file."
        )
        sys.exit(1)

    try:
        contacts = load_contacts(args.contacts)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Contact load error: %s", e)
        sys.exit(1)

    if not contacts:
        logger.error("No valid contacts found. Check your CSV.")
        sys.exit(1)

    client = WhatsAppClient(phone_number_id, access_token)

    send_blast(
        client,
        contacts,
        message_template=args.message,
        wa_template_name=args.template,
        wa_template_language=args.template_lang,
        wa_template_body_vars=args.template_vars,
        delay=args.delay,
        dry_run=args.dry_run,
        on_progress=progress_bar,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
