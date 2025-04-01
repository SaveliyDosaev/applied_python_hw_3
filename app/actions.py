from datetime import datetime, timedelta
import string
import random
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder
import json
from . import schemas, db as database


def cleanup_inactive_links(db: Session, days_inactive: int):
    cutoff = datetime.utcnow() - timedelta(days=days_inactive)
    inactive_links = db.query(schemas.ShortLink).filter(schemas.ShortLink.last_accessed < cutoff).all()
    
    for link in inactive_links:
        database.redis.delete(f"link:{link.short_code}")
        if link.project:
            database.redis.delete(f"project_links:{link.project}")
        db.delete(link)
    
    db.commit()
    return len(inactive_links)


def get_links_by_project(db: Session, project: str):
    cached = database.redis.get(f"project_links:{project}")
    if cached:
        return [schemas.ShortLinkResponse.model_validate_json(item) for item in json.loads(cached)]
    
    links = db.query(schemas.ShortLink).filter(schemas.ShortLink.project == project).all()
    result = [schemas.ShortLinkResponse.model_validate(link) for link in links]
    
    if result:
        database.redis.setex(f"project_links:{project}", 3600, json.dumps([jsonable_encoder(item) for item in result]))
    
    return result


def create_link(db: Session, link: schemas.ShortLinkCreate):
    short_code = link.custom_alias or generate_unique_alias()
    db_link = schemas.ShortLink(
        original_url=link.original_url,
        short_code=short_code,
        created_at=datetime.utcnow(),
        expires_at=link.expires_at,
        project=link.project
    )
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    
    response = schemas.ShortLinkResponse.model_validate(db_link)
    database.redis.setex(f"link:{short_code}", 3600, json.dumps(jsonable_encoder(response)))
    
    return response


def get_link_by_alias(db: Session, alias: str):
    cached = database.redis.get(f"link:{alias}")
    if cached:
        return schemas.ShortLinkResponse.model_validate_json(cached)
    
    db_link = db.query(schemas.ShortLink).filter(schemas.ShortLink.short_code == alias).first()
    
    if not db_link:
        return None
    
    response = schemas.ShortLinkResponse.model_validate(db_link)
    database.redis.setex(f"link:{alias}", 3600, json.dumps(jsonable_encoder(response)))
    
    return response


def increment_click_count(db: Session, link: schemas.ShortLink):
    if not isinstance(link, schemas.ShortLink):
        link = db.query(schemas.ShortLink).filter(schemas.ShortLink.short_code == link.short_code).first()
    
    link.click_count += 1
    link.last_accessed = datetime.now()
    db.commit()
    db.refresh(link)
    
    response = schemas.ShortLinkResponse.model_validate(link)
    database.redis.setex(f"link:{link.short_code}", 3600, json.dumps(jsonable_encoder(response)))
    
    return response


def delete_link(db: Session, link: schemas.ShortLink):
    if not isinstance(link, schemas.ShortLink):
        link = db.query(schemas.ShortLink).filter(schemas.ShortLink.short_code == link.short_code).first()
    
    if link:
        database.redis.delete(f"link:{link.short_code}")
        if link.project:
            database.redis.delete(f"project_links:{link.project}")
        db.delete(link)
        db.commit()


def update_link(db: Session, link: schemas.ShortLink, link_update: schemas.ShortLinkUpdate):
    if not isinstance(link, schemas.ShortLink):
        link = db.query(schemas.ShortLink).filter(schemas.ShortLink.short_code == link.short_code).first()
    
    if not link:
        return None
    
    database.redis.delete(f"link:{link.short_code}")
    if link.project:
        database.redis.delete(f"project_links:{link.project}")
    
    link.original_url = link_update.original_url
    db.commit()
    db.refresh(link)
    
    response = schemas.ShortLinkResponse.model_validate(link)
    database.redis.setex(f"link:{link.short_code}", 3600, json.dumps(jsonable_encoder(response)))
    
    return response


def generate_unique_alias(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def search_links_by_original_url(db: Session, original_url: str):
    cache_key = f"search:{original_url}"
    cached = database.redis.get(cache_key)
    if cached:
        return [schemas.ShortLinkSearchResult(**link) for link in json.loads(cached)]
    
    links = db.query(schemas.ShortLink).filter(schemas.ShortLink.original_url.ilike(f"%{original_url}%")).all()
    result = [schemas.ShortLinkSearchResult.model_validate(link) for link in links]
    
    if result:
        database.redis.setex(cache_key, 3600, json.dumps(jsonable_encoder(result)))
    
    return result