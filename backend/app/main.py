from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import Base, engine
from .routers import auth, blogs, categories, posts, users
from .services.storage import STATIC_ROOT


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)  # swap for Alembic once the schema starts changing
    categories.seed()
    yield


app = FastAPI(title="Blog Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")
app.include_router(auth.router)
app.include_router(blogs.router)
app.include_router(posts.router)
app.include_router(users.router)
app.include_router(categories.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
