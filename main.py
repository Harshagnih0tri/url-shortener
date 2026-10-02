import os
import secrets
import string
from datetime import timezone
from urllib.parse import urlparse

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Url, Click, utcnow
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
            return {
                "code": link.code,
                "shortUrl": f"{BASE_URL}/{link.code}",
                "url": link.original_url,
                "expiresAt": link.expires_at,
            }
        except IntegrityError:
            db.rollback()

    raise HTTPException(500, "Could not generate a unique code")

def get_link(db, code):
    link = db.query(Url).filter(Url.code == code).first()
    if not link:
        raise HTTPException(404, "Short URL not found")
    return link


@app.get("/{code}")
def redirect(code: str, request: Request, db: Session = Depends(get_db)):
    link = get_link(db, code)

    if link.expires_at and link.expires_at <= utcnow():
        raise HTTPException(410, "This link has expired")

    db.add(Click(
        url_id=link.id,
        user_agent=request.headers.get("user-agent"),
        referrer=request.headers.get("referer"),
    ))
    db.commit()

    return RedirectResponse(link.original_url, status_code=302)