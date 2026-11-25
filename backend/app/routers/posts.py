"""Public feed, post pages and comments."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user, get_optional_user
from ..models import Blog, Category, Comment, User
from ..schemas import AuthorOut, CategoryOut, CommentCreate, CommentOut, PostCard, PostDetail, PostList

router = APIRouter(prefix="/api/posts", tags=["posts"])


def _counts(db: Session, ids: list[int]) -> dict[int, int]:
    if not ids:
        return {}
    rows = db.execute(select(Comment.blog_id, func.count()).where(Comment.blog_id.in_(ids)).group_by(Comment.blog_id)).all()
    return {bid: n for bid, n in rows}


def _card(b: Blog, count: int) -> dict:
    return dict(
        id=b.id,
        title=b.title or b.topic,
        excerpt=b.excerpt,
        cover_url=b.cover_url,
        category=CategoryOut.model_validate(b.category) if b.category else None,
        author=AuthorOut.model_validate(b.user),
        created_at=b.created_at,
        comment_count=count,
    )


def _visible_or_404(db: Session, post_id: int, user: User | None) -> Blog:
    blog = db.get(Blog, post_id)
    if not blog or blog.status != "completed":
        raise HTTPException(404, "Post not found")
    if not blog.is_published and (user is None or user.id != blog.user_id):
        raise HTTPException(404, "Post not found")
    return blog


@router.get("", response_model=PostList)
def feed(
    category: str | None = Query(None, description="category slug"),
    q: str | None = None,
    author_id: int | None = None,
    limit: int = Query(12, ge=1, le=60),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Blog).where(Blog.status == "completed", Blog.is_published.is_(True))
    if category:
        stmt = stmt.join(Category, Blog.category_id == Category.id).where(Category.slug == category)
    if author_id:
        stmt = stmt.where(Blog.user_id == author_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Blog.title.ilike(like), Blog.excerpt.ilike(like)))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.options(selectinload(Blog.user), selectinload(Blog.category))
        .order_by(Blog.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    counts = _counts(db, [b.id for b in rows])
    return PostList(items=[PostCard(**_card(b, counts.get(b.id, 0))) for b in rows], total=total)


@router.get("/{post_id}", response_model=PostDetail)
def get_post(post_id: int, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)):
    blog = _visible_or_404(db, post_id, user)
    count = _counts(db, [blog.id]).get(blog.id, 0)
    return PostDetail(
        **_card(blog, count),
        markdown=blog.markdown,
        is_published=blog.is_published,
        mode=blog.mode,
        evidence=blog.evidence,
    )


# ---------- comments ----------
def _comment_out(c: Comment) -> CommentOut:
    return CommentOut(id=c.id, body=c.body, created_at=c.created_at, author=AuthorOut.model_validate(c.user))


@router.get("/{post_id}/comments", response_model=list[CommentOut])
def list_comments(post_id: int, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)):
    _visible_or_404(db, post_id, user)
    rows = db.scalars(
        select(Comment).where(Comment.blog_id == post_id).options(selectinload(Comment.user)).order_by(Comment.created_at)
    ).all()
    return [_comment_out(c) for c in rows]


@router.post("/{post_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(post_id: int, body: CommentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _visible_or_404(db, post_id, user)
    comment = Comment(blog_id=post_id, user_id=user.id, body=body.body.strip())
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return _comment_out(comment)


@router.delete("/{post_id}/comments/{comment_id}", status_code=204)
def delete_comment(post_id: int, comment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    comment = db.get(Comment, comment_id)
    if not comment or comment.blog_id != post_id:
        raise HTTPException(404, "Comment not found")
    blog = db.get(Blog, post_id)
    # the commenter or the post's author can remove a comment
    if comment.user_id != user.id and blog.user_id != user.id:
        raise HTTPException(403, "You can't delete this comment")
    db.delete(comment)
    db.commit()
