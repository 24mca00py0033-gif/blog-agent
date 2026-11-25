from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal, get_db
from ..models import Category
from ..schemas import CategoryOut
from ..utils import slugify

router = APIRouter(prefix="/api/categories", tags=["categories"])

DEFAULT_CATEGORIES = [
    "AI & Machine Learning", "Programming", "Web Development", "Data Science",
    "DevOps & Cloud", "Technology", "Science", "Career", "Productivity", "Other",
]


def seed() -> None:
    db = SessionLocal()
    try:
        existing = {c.name for c in db.scalars(select(Category))}
        for name in DEFAULT_CATEGORIES:
            if name not in existing:
                db.add(Category(name=name, slug=slugify(name)))
        db.commit()
    finally:
        db.close()


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    # keep the seed order (Other last) rather than alphabetical
    order = {n: i for i, n in enumerate(DEFAULT_CATEGORIES)}
    cats = db.scalars(select(Category)).all()
    return sorted(cats, key=lambda c: order.get(c.name, 999))
