import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Blog, User
from ..schemas import ProfileOut, ProfileUpdate, UserOut
from ..services.storage import upload_image

router = APIRouter(prefix="/api/users", tags=["users"])

ALLOWED = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
MAX_AVATAR_BYTES = 5 * 1024 * 1024


@router.patch("/me", response_model=UserOut)
def update_me(body: ProfileUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    data = body.model_dump(exclude_unset=True)
    if data.get("name") is not None:
        user.name = data["name"].strip()
    if data.get("bio") is not None:
        user.bio = data["bio"].strip()
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ext = ALLOWED.get(file.content_type or "")
    if not ext:
        raise HTTPException(415, "Use a PNG, JPEG or WebP image")
    data = await file.read()
    if len(data) > MAX_AVATAR_BYTES:
        raise HTTPException(413, "Image must be under 5 MB")
    # unique id so browsers don't keep showing the old cached avatar
    user.avatar_url = upload_image(data, "draftroom/avatars", f"user_{user.id}_{uuid.uuid4().hex[:8]}", ext)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=ProfileOut)
def get_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    count = db.scalar(
        select(func.count()).select_from(Blog).where(
            Blog.user_id == user_id, Blog.status == "completed", Blog.is_published.is_(True)
        )
    )
    return ProfileOut(
        id=user.id, name=user.name, avatar_url=user.avatar_url, bio=user.bio,
        created_at=user.created_at, post_count=count or 0,
    )
