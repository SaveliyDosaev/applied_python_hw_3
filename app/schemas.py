from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime
from . import db

class ShortLinkBase(BaseModel):
    class Config:
        from_attributes = True

class ShortLinkCreate(ShortLinkBase):
    original_url: str
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None
    project: Optional[str] = None

class ShortLinkResponse(ShortLinkBase):
    original_url: str
    short_code: str
    created_at: datetime
    expires_at: Optional[datetime]
    click_count: int
    last_accessed: Optional[datetime]
    project: Optional[str]

class ShortLinkUpdate(ShortLinkBase):
    original_url: str

class ShortLinkStats(ShortLinkBase):
    original_url: str
    short_code: str
    created_at: datetime
    click_count: int
    last_accessed: Optional[datetime]

class ShortLinkSearchResult(ShortLinkBase):
    original_url: str
    short_code: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    click_count: int

class ShortLink(db.Base):
    __tablename__ = "short_links_55"
    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String, index=True)
    short_code = Column(String, unique=True, index=True)
    created_at = Column(DateTime)
    expires_at = Column(DateTime)
    last_accessed = Column(DateTime)
    click_count = Column(Integer, default=0)
    project = Column(String, nullable=True)