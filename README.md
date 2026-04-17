# WhatsApp Blast — Python + Meta Business API

A lightweight CLI tool to send bulk WhatsApp messages using the
**Meta WhatsApp Business Cloud API**.

---

## Prerequisites

1. A Meta Developer account → https://developers.facebook.com
2. A WhatsApp Business app with a verified phone number
3. Python 3.11+

---

## Setup

### 1. Get your credentials

Go to: https://developers.facebook.com/apps → your app → **WhatsApp → API Setup**

You need:
- **Phone Number ID** (not the phone number itself)
- **Access Token** (use a permanent System User token for production)

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure credentials

```bash
cp .env.example .env
# Edit .env and fill in WA_PHONE_NUMBER_ID and WA_ACCESS_TOKEN
```

### 4. Prepare your contacts

Edit `contacts_sample.csv` or create your own. Required column: `phone` (digits only, with country code, no `+`).

```csv
phone,name,promo_code
628123456789,Andi,SAVE20
628234567890,Budi,SAVE30
```

---

## Usage

### Send a free-form text blast
> Only works within the **24-hour customer service window** (user must have messaged you first).

```bash
python main.py \
  --contacts contacts_sample.csv \
  --message "Hi {{name}}, your exclusive code is {{promo_code}}. Shop now!"
```

### Send an approved template blast
> Works anytime — required for proactive/marketing messages.
> Template must be approved in Meta Business Manager first.

```bash
python main.py \
  --contacts contacts_sample.csv \
  --template your_template_name \
  --template-lang en_US \
  --template-vars name promo_code
```

### Dry run (preview, no messages sent)

```bash
python main.py --contacts contacts_sample.csv --message "Hi {{name}}!" --dry-run
```

### Control send rate

```bash
# 2 seconds between messages (default is 1.0)
python main.py --contacts contacts_sample.csv --message "Hi {{name}}!" --delay 2.0
```

---

## Message variables

Use `{{column_name}}` in your message text. These are replaced per contact using CSV column values.

| Placeholder     | Source            |
|-----------------|-------------------|
| `{{name}}`      | `name` column     |
| `{{phone}}`     | `phone` column    |
| `{{promo_code}}`| `promo_code` column (or any custom column) |

---

## Output

After each blast, a `blast_report_YYYYMMDD_HHMMSS.csv` is saved with:

| phone | name | status | message_id | error |
|-------|------|--------|------------|-------|
| 628... | Andi | sent | wamid.xxx | |
| 628... | Budi | failed | | Invalid phone |

---

## Project structure

```
wa_blast/
├── main.py          # CLI entry point
├── client.py        # Meta API client
├── blast.py         # Blast engine (rate limiting, retries, reporting)
├── contacts.py      # CSV loader & message renderer
├── contacts_sample.csv
├── .env.example
├── requirements.txt
└── README.md
```

---

## Rate limits & best practices

- **Default delay**: 1 second between messages (safe for most tiers)
- The app retries failed messages up to 2 times automatically
- Use **approved templates** for marketing blasts — free-form text outside the 24hr window will fail
- Keep message content relevant and opt-in compliant to avoid being flagged

---

## Getting a permanent access token

The default token from API Setup expires in 24 hours. For production:

1. Go to Meta Business Manager → **System Users**
2. Create a System User and assign the WhatsApp app
3. Generate a token with `whatsapp_business_messaging` permission
4. Paste it in your `.env` file
