import os
import secrets
import string
from collections import Counter
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
CHARS = string.ascii_letters + string.digits

Base.metadata.create_all(bind=engine)
app = FastAPI()


@app.exception_handler(HTTPException)
def http_error(request, exc):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
def bad_body(request, exc):
    return JSONResponse({"error": "Invalid request body"}, status_code=400)


def get_link(db, code):
    link = db.query(Url).filter_by(code=code).first()
    if not link:
        raise HTTPException(404, "Short URL not found")
    return link


def to_json(link):
    return {
        "code": link.code,
        "shortUrl": f"{BASE_URL}/{link.code}",
        "url": link.original_url,
        "createdAt": link.created_at,
        "expiresAt": link.expires_at,
    }


@app.post("/api/urls", status_code=201)
def create_url(data: UrlCreate, db: Session = Depends(get_db)):
    parts = urlparse(data.url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise HTTPException(400, "url must be a valid http or https URL")

    expires = data.expiresAt
    if expires:
        if expires.tzinfo:
            expires = expires.astimezone(timezone.utc).replace(tzinfo=None)
        if expires <= utcnow():
            raise HTTPException(400, "expiresAt must be in the future")

    # random codes can collide, so retry a few times
    for attempt in range(5):
        code = "".join(secrets.choice(CHARS) for i in range(7))
        link = Url(code=code, original_url=data.url, expires_at=expires)
        db.add(link)
        try:
            db.commit()
            return to_json(link)
        except IntegrityError:
            db.rollback()

    raise HTTPException(500, "Could not generate a unique code")


@app.get("/api/urls")
def list_urls(page: int = 1, limit: int = 20, db: Session = Depends(get_db)):
    if page < 1 or not 1 <= limit <= 100:
        raise HTTPException(400, "page must be >= 1 and limit between 1 and 100")

    links = (
        db.query(Url)
        .order_by(Url.created_at.desc(), Url.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return {"page": page, "limit": limit, "total": db.query(Url).count(),
            "items": [to_json(l) for l in links]}


@app.get("/api/urls/{code}/stats")
def get_stats(code: str, db: Session = Depends(get_db)):
    link = get_link(db, code)
    times = [c.clicked_at for c in link.clicks]
    per_day = Counter(t.date().isoformat() for t in times)

    return {
        "code": link.code,
        "url": link.original_url,
        "totalClicks": len(times),
        "createdAt": link.created_at,
        "lastClickedAt": max(times, default=None),
        "clicksByDay": [{"date": d, "count": n} for d, n in sorted(per_day.items())],
    }


@app.delete("/api/urls/{code}", status_code=204)
def delete_url(code: str, db: Session = Depends(get_db)):
    db.delete(get_link(db, code))
    db.commit()


# keep this last, otherwise it would catch /docs too
@app.get("/{code}")
def redirect(code: str, request: Request, db: Session = Depends(get_db)):
    link = get_link(db, code)
    if link.expires_at and link.expires_at <= utcnow():
        raise HTTPException(410, "This link has expired")

    db.add(Click(url_id=link.id,
                 user_agent=request.headers.get("user-agent"),
                 referrer=request.headers.get("referer")))
    db.commit()
    return RedirectResponse(link.original_url, status_code=302)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=int(os.getenv("PORT", 8000)))