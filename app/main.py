from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List
from . import schemas, actions, db
from datetime import datetime

db.Base.metadata.create_all(bind=db.engine)

app = FastAPI()

def get_db():
    database = db.SessionLocal()
    try:
        yield database
    finally:
        database.close()

@app.post("/links/shorten", response_model=schemas.ShortLinkResponse)
def create_short_link(link: schemas.ShortLinkCreate, db: Session = Depends(get_db)):
    if link.custom_alias:
        db_link = actions.get_link_by_alias(db, alias=link.custom_alias)
        if db_link:
            raise HTTPException(status_code=400, detail="Alias already exists")
    else:
        link.custom_alias = actions.generate_unique_alias()

    db_link = actions.create_link(db, link)
    return db_link

@app.get("/{short_code}")
def redirect_to_original(short_code: str, db: Session = Depends(get_db)):
    db_link = actions.get_link_by_alias(db, alias=short_code)
    if not db_link:
        raise HTTPException(status_code=404, detail="Link not found")
    if db_link.expires_at and db_link.expires_at < datetime.utcnow():
        actions.delete_link(db, db_link)
        raise HTTPException(status_code=410, detail="Link has expired and been deleted")
    
    actions.increment_click_count(db, db_link)
    return RedirectResponse(url=db_link.original_url)

@app.get("/links/project/{project}", response_model=List[schemas.ShortLinkResponse])
def get_project_links(project: str, db: Session = Depends(get_db)):
    return actions.get_links_by_project(db, project)

@app.post("/links/cleanup/{days_inactive}")
def cleanup_links(days_inactive: int, db: Session = Depends(get_db)):
    return {"deleted": actions.cleanup_inactive_links(db, days_inactive)}

@app.delete("/links/{short_code}")
def delete_link(short_code: str, database: Session = Depends(get_db)):
    db_link = actions.get_link_by_alias(database, alias=short_code)
    if not db_link:
        raise HTTPException(status_code=404, detail="Link not found")
    actions.delete_link(database, db_link)
    return {"message": "Link deleted"}

@app.put("/links/{short_code}", response_model=schemas.ShortLinkResponse)
def update_link(short_code: str, link: schemas.ShortLinkUpdate, database: Session = Depends(get_db)):
    db_link = actions.get_link_by_alias(database, alias=short_code)
    if not db_link:
        raise HTTPException(status_code=404, detail="Link not found")
    return actions.update_link(database, db_link, link)

@app.get("/links/{short_code}/stats", response_model=schemas.ShortLinkStats)
def get_link_stats(short_code: str, database: Session = Depends(get_db)):
    db_link = actions.get_link_by_alias(database, alias=short_code)
    if not db_link:
        raise HTTPException(status_code=404, detail="Link not found")
    return db_link

@app.get("/links/search", response_model=List[schemas.ShortLinkSearchResult])
def search_links(
    original_url: str = Query(description="Original URL to search for"),
    db: Session = Depends(get_db)
):
    links = actions.search_links_by_original_url(db, original_url)
    if not links:
        raise HTTPException(
            status_code=404,
            detail="No links found matching the search criteria"
        )
    return links