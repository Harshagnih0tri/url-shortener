import os
import secrets
import string
from datetime import timezone
from urllib.parse import urlparse

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Url, utcnow
from schemas import UrlCreate

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

Base.metadata.create_all(bind=engine)
app = FastAPI(title="URL Shortener")


@app.exception_handler(HTTPException)
def http_error(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(RequestValidationError)
def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "Invalid request body"})


def generate_code(length=7):
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def is_valid_url(url):
    parts = urlparse(url)
    return parts.scheme in ("http", "https") and bool(parts.netloc)


@app.post("/api/urls", status_code=201)
def create_url(data: UrlCreate, db: Session = Depends(get_db)):
    if not is_valid_url(data.url):
        raise HTTPException(400, "url must be a valid http or https URL")

    expires_at = None
    if data.expiresAt:
        expires_at = data.expiresAt
        if expires_at.tzinfo:
            expires_at = expires_at.astimezone(timezone.utc).replace(tzinfo=None)
        if expires_at <= utcnow():
            raise HTTPException(400, "expiresAt must be in the future")

   
    for _ in range(5):
        link = Url(code=generate_code(), original_url=data.url, expires_at=expires_at)
        db.add(link)
        try:
            db.commit()
            break
        except IntegrityError:
            db.rollback()
    else:
        raise HTTPException(500, "Could not generate a unique code")

    return {
        "code": link.code,
        "shortUrl": f"{BASE_URL}/{link.code}",
        "url": link.original_url,
        "expiresAt": link.expires_at,
    }