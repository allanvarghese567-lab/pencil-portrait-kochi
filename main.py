"""
Pencil Portrait Artist — FastAPI backend
Serves the static site and handles portrait orders via SMTP.
"""

import os
import re
from email.message import EmailMessage
from pathlib import Path
from typing import List, Optional

import smtplib
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
MAIL_TO = os.getenv("MAIL_TO", "")

MAX_FILES = 3
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

BASE_DIR = Path(__file__).resolve().parent
PHOTOS_DIR = BASE_DIR / "photos"

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Pencil Portrait Orders", docs_url=None, redoc_url=None)

# Serve gallery images
if PHOTOS_DIR.is_dir():
    app.mount("/photos", StaticFiles(directory=str(PHOTOS_DIR)), name="photos")


@app.get("/")
async def index():
    return FileResponse(BASE_DIR / "index.html")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value)) and len(value) <= 120


def clean(text: Optional[str], max_len: int = 500) -> str:
    if not text:
        return ""
    return text.strip()[:max_len]


# ---------------------------------------------------------------------------
# Order endpoint
# ---------------------------------------------------------------------------

@app.post("/api/order")
async def create_order(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    occasion: str = Form(...),
    size: str = Form(...),
    needed_by: Optional[str] = Form(None),
    message: Optional[str] = Form(None),
    website: Optional[str] = Form(None),  # honeypot
    photos: List[UploadFile] = File(default=[]),
):
    # Honeypot — bots fill this; real users leave it empty
    if website and website.strip():
        return JSONResponse({"message": "Order received. Thank you!"})

    # Field validation
    name = clean(name, 100)
    email = clean(email, 120)
    phone = clean(phone, 20)
    occasion = clean(occasion, 40)
    size = clean(size, 60)
    needed_by = clean(needed_by, 20) if needed_by else ""
    message = clean(message, 1000) if message else ""

    errors = []
    if not name:
        errors.append("Name is required.")
    if not email or not validate_email(email):
        errors.append("A valid email address is required.")
    if not phone:
        errors.append("Phone / WhatsApp is required.")
    if not occasion:
        errors.append("Occasion is required.")
    if not size:
        errors.append("Size is required.")

    # Photo validation
    if not photos or len(photos) == 0:
        errors.append("At least one reference photo is required.")
    elif len(photos) > MAX_FILES:
        errors.append(f"Maximum {MAX_FILES} photos allowed.")
    else:
        for photo in photos:
            content_type = (photo.content_type or "").lower()
            ext = Path(photo.filename or "").suffix.lower()
            if content_type not in ALLOWED_TYPES and ext not in ALLOWED_EXTENSIONS:
                errors.append("Only JPG, PNG and WebP images are allowed.")
                break
            # Size check requires reading; we check after read below

    if errors:
        raise HTTPException(status_code=400, detail=" ".join(errors))

    # Read and size-check files
    attachments = []
    for photo in photos:
        data = await photo.read()
        if len(data) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail="Each photo must be under 5 MB.",
            )
        if len(data) == 0:
            continue
        attachments.append((photo.filename or "photo.jpg", data, photo.content_type or "image/jpeg"))

    if not attachments:
        raise HTTPException(status_code=400, detail="At least one valid photo is required.")

    # Build email
    body_lines = [
        "New pencil portrait order",
        "========================",
        f"Name:     {name}",
        f"Email:    {email}",
        f"Phone:    {phone}",
        f"Occasion: {occasion}",
        f"Size:     {size}",
        f"Needed by: {needed_by or 'Not specified'}",
        "",
        "Message:",
        message or "(none)",
        "",
        f"Attachments: {len(attachments)} photo(s)",
    ]
    body = "\n".join(body_lines)

    msg = EmailMessage()
    msg["Subject"] = f"Portrait order from {name} — {size}"
    msg["From"] = SMTP_USER
    msg["To"] = MAIL_TO
    msg["Reply-To"] = email
    msg.set_content(body)

    for filename, data, content_type in attachments:
        maintype, subtype = (content_type or "image/jpeg").split("/", 1)
        msg.add_attachment(
            data,
            maintype=maintype,
            subtype=subtype,
            filename=filename,
        )

    # Send
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS, MAIL_TO]):
        # Misconfigured — do not expose details
        raise HTTPException(
            status_code=503,
            detail="Order service is temporarily unavailable. Please try again later.",
        )

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
    except Exception:
        # Never leak SMTP errors to the client
        raise HTTPException(
            status_code=503,
            detail="Could not send the order right now. Please try again in a few minutes.",
        )

    return JSONResponse(
        {"message": "Order sent successfully. The artist will reply soon."}
    )


# ---------------------------------------------------------------------------
# Health (useful for Render / Railway)
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}
