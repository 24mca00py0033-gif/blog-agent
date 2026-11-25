"""Owner-only blog management: generate, write manually, edit, delete."""
import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal, get_db
from ..deps import get_current_user
from ..models import Blog, Category, User
from ..schemas import BlogCreate, BlogDetail, BlogManualCreate, BlogSummary, BlogUpdate
from ..services.blog_agent import classify_category, run_blog_agent
from ..services.storage import delete_folder
from ..utils import first_image_url, make_excerpt

router = APIRouter(prefix="/api/blogs", tags=["blogs"])


def _get_owned(db: Session, blog_id: int, user: User) -> Blog:
    blog = db.get(Blog, blog_id)
    if not blog or blog.user_id != user.id:
        raise HTTPException(404, "Blog not found")
    return blog


def _check_category(db: Session, category_id: int | None) -> None:
    if category_id is not None and not db.get(Category, category_id):
        raise HTTPException(422, "Unknown category")


def _generate(blog_id: int) -> None:
    """Runs in a worker thread after the POST returns."""
    db = SessionLocal()
    try:
        blog = db.get(Blog, blog_id)
        if not blog:
            return
        blog.status, blog.progress = "running", "Starting"
        db.commit()

        def on_step(msg: str) -> None:
            blog.progress = msg
            db.commit()

        result = run_blog_agent(blog.topic, blog_id, on_step)
        blog.title = result["title"][:300]
        blog.markdown = result["markdown"]
        blog.mode = result["mode"]
        blog.plan = result["plan"]
        blog.evidence = result["evidence"]
        blog.excerpt = make_excerpt(blog.markdown)
        blog.cover_url = first_image_url(blog.markdown)

        if blog.category_id is None:
            on_step("Choosing a category")
            cats = {c.name: c.id for c in db.scalars(select(Category))}
            name = classify_category(blog.title, blog.topic, list(cats)) if cats else None
            blog.category_id = cats.get(name) if name else None

        blog.status, blog.progress = "completed", "Done"
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        blog = db.get(Blog, blog_id)
        if blog:
            blog.status, blog.progress, blog.error = "failed", "Failed", str(e)[:2000]
            db.commit()
    finally:
        db.close()


@router.post("", response_model=BlogSummary, status_code=202)
def create_blog(
    body: BlogCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Start AI generation. Poll GET /api/blogs/{id} for progress."""
    _check_category(db, body.category_id)
    blog = Blog(user_id=user.id, topic=body.topic.strip(), category_id=body.category_id, status="pending", progress="Queued")
    db.add(blog)
    db.commit()
    db.refresh(blog)
    background.add_task(_generate, blog.id)
    return blog


@router.post("/manual", response_model=BlogDetail, status_code=201)
def create_manual(body: BlogManualCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Publish a post you wrote yourself (no AI)."""
    _check_category(db, body.category_id)
    blog = Blog(
        user_id=user.id,
        topic=body.title.strip(),
        title=body.title.strip(),
        markdown=body.markdown,
        excerpt=make_excerpt(body.markdown),
        cover_url=first_image_url(body.markdown),
        category_id=body.category_id,
        is_published=body.is_published,
        status="completed",
        progress="Done",
    )
    db.add(blog)
    db.commit()
    db.refresh(blog)
    return blog


@router.get("", response_model=list[BlogSummary])
def list_my_blogs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(select(Blog).where(Blog.user_id == user.id).order_by(Blog.created_at.desc())).all()


@router.get("/{blog_id}", response_model=BlogDetail)
def get_my_blog(blog_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _get_owned(db, blog_id, user)


@router.patch("/{blog_id}", response_model=BlogDetail)
def update_blog(blog_id: int, body: BlogUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    blog = _get_owned(db, blog_id, user)
    if blog.status in ("pending", "running"):
        raise HTTPException(409, "This post is still being generated")
    data = body.model_dump(exclude_unset=True)

    if "title" in data and data["title"] is not None:
        blog.title = data["title"].strip()
    if "markdown" in data and data["markdown"] is not None:
        blog.markdown = data["markdown"]
        blog.excerpt = make_excerpt(blog.markdown)
        blog.cover_url = first_image_url(blog.markdown)
    if "category_id" in data:
        _check_category(db, data["category_id"])
        blog.category_id = data["category_id"]
    if "is_published" in data and data["is_published"] is not None:
        blog.is_published = data["is_published"]
    db.commit()
    db.refresh(blog)
    return blog


@router.get("/{blog_id}/download")
def download_blog(blog_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    blog = _get_owned(db, blog_id, user)
    return Response(
        blog.markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="blog-{blog.id}.md"'},
    )


@router.delete("/{blog_id}", status_code=204)
def delete_blog(blog_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    blog = _get_owned(db, blog_id, user)
    db.delete(blog)  # comments are removed with it
    db.commit()
    delete_folder(f"draftroom/blog_{blog_id}")
