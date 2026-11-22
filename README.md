# Pencil Portrait Artist — Kochi

A single-page site + FastAPI backend for a pencil portrait artist. Visitors browse the gallery and submit orders with reference photos; orders are emailed to the artist over SMTP.

## Stack

- **Frontend:** one `index.html` (inline CSS + vanilla JS)
- **Backend:** FastAPI + uvicorn
- **Email:** smtplib + STARTTLS, credentials from `.env`

## Quick start

```bash
# 1. Clone and enter the repo
cd pencil-portrait-kochi   # or whatever you named the folder

# 2. Create a virtualenv (recommended)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your SMTP credentials (see below)

# 5. Add gallery images (optional)
mkdir -p photos
# Drop portrait-1.jpg … portrait-4.jpg into photos/

# 6. Run
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000

## Gmail App Password setup

1. Enable 2-Step Verification on the Google account that will send mail.
2. Go to [Google Account → App passwords](https://myaccount.google.com/apppasswords).
3. Generate a password for “Mail”.
4. Put that 16-character password in `SMTP_PASS` (not your normal Gmail password).
5. Set `SMTP_USER` and `MAIL_TO` to the same address (or different if you want orders delivered elsewhere).

## Environment variables

| Variable    | Description                          |
|-------------|--------------------------------------|
| SMTP_HOST   | e.g. `smtp.gmail.com`                |
| SMTP_PORT   | usually `587` (STARTTLS)             |
| SMTP_USER   | login email                          |
| SMTP_PASS   | App Password                         |
| MAIL_TO     | where order emails are delivered     |

## API

`POST /api/order` — multipart form data

- Fields: `name`, `email`, `phone`, `occasion`, `size`, `needed_by` (optional), `message` (optional), `website` (honeypot)
- Files: `photos` (1–3 images, JPG/PNG/WebP, ≤5 MB each)
- Returns JSON success or clear validation errors
- Never exposes raw SMTP errors to the client

## Deployment (Render / Railway)

1. Push this repo to GitHub.
2. Create a new **Web Service**.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add the five environment variables from `.env.example` in the dashboard.
6. Deploy. The free tier is enough for light traffic.

On Render, set the health check path to `/health` if available.

## Notes

- Gallery images live in `/photos`. Missing images show a hatched-paper placeholder.
- The form has client-side validation, a honeypot field, and an `aria-live` status region.
- Design follows a graphite pencil feel with light/dark mode via `prefers-color-scheme`.
