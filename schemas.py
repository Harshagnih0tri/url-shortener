from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class UrlCreate(BaseModel):
    url: str
    expiresAt: Optional[datetime] = None