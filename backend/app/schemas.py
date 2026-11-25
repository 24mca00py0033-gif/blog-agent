from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- auth / users ----------
class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: EmailStr
    bio: str = ""
    avatar_url: str = ""


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class AuthorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    avatar_url: str = ""


class ProfileOut(AuthorOut):
    bio: str = ""
    created_at: datetime
    post_count: int = 0


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    bio: Optional[str] = Field(default=None, max_length=500)


# ---------- categories ----------
class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str


# ---------- public posts ----------
class PostCard(BaseModel):
    id: int
    title: str
    excerpt: str
    cover_url: str
    category: Optional[CategoryOut] = None
    author: AuthorOut
    created_at: datetime
    comment_count: int = 0


class PostList(BaseModel):
    items: list[PostCard]
    total: int


class PostDetail(PostCard):
    markdown: str
    is_published: bool
    mode: str = ""
    evidence: Optional[list[Any]] = None


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class CommentOut(BaseModel):
    id: int
    body: str
    created_at: datetime
    author: AuthorOut


# ---------- owner blog management ----------
class BlogCreate(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    category_id: Optional[int] = None  # None -> the agent picks one


class BlogManualCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    markdown: str = Field(min_length=1)
    category_id: Optional[int] = None
    is_published: bool = True


class BlogUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    markdown: Optional[str] = Field(default=None, min_length=1)
    category_id: Optional[int] = None
    is_published: Optional[bool] = None


class BlogSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    topic: str
    title: str
    status: str
    progress: str
    mode: str
    is_published: bool
    cover_url: str
    category: Optional[CategoryOut] = None
    created_at: datetime


class BlogDetail(BlogSummary):
    markdown: str
    plan: Optional[dict[str, Any]] = None
    evidence: Optional[list[Any]] = None
    error: str = ""
