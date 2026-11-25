# Draftroom – AI blog writing agent

FastAPI + LangGraph (Groq) backend · React (Vite) frontend · Neon PostgreSQL · JWT auth · Hugging Face images

```
blog-agent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, static files, table creation
│   │   ├── config.py            # settings from .env
│   │   ├── database.py          # SQLAlchemy engine/session (Neon)
│   │   ├── models.py            # User, Blog
│   │   ├── schemas.py           # request/response models
│   │   ├── security.py          # bcrypt hashing + JWT
│   │   ├── deps.py              # get_current_user dependency
│   │   ├── routers/auth.py      # signup / login / me
│   │   ├── routers/users.py     # profile, avatar upload
│   │   ├── routers/posts.py     # public feed, post page, comments
│   │   ├── routers/blogs.py     # generate, write, edit, delete (owner)
│   │   ├── routers/categories.py
│   │   └── services/
│   │       ├── blog_agent.py    # your LangGraph pipeline (Groq) + category classifier
│   │       ├── storage.py       # Cloudinary upload/delete (local fallback)
│   │       └── image_service.py # Hugging Face text-to-image
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    └── src/ (api.js, auth.jsx, pages/, components/, styles.css)
```

## Run it

### 1. Backend
```bash
cd backend
python -m venv venv && venv\Scripts\activate      # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                            # then fill in the values
uvicorn app.main:app --reload --port 8000
```
Tables are created on startup. API docs: http://localhost:8000/docs

### 2. Frontend
```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```
Open http://localhost:5173

## API
Auth = `Authorization: Bearer <jwt>`. Interactive docs at `/docs`.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | /api/auth/signup, /login | – | returns JWT + user |
| GET | /api/auth/me | yes | current user |
| GET | /api/users/{id} | – | public profile + post count |
| PATCH | /api/users/me | yes | edit name / bio |
| POST | /api/users/me/avatar | yes | upload profile photo (Cloudinary) |
| GET | /api/categories | – | category list |
| GET | /api/posts | – | home feed: `?category=<slug>&q=<text>&author_id=&limit=&offset=` |
| GET | /api/posts/{id} | optional | one published post (owner can also see own drafts) |
| GET/POST | /api/posts/{id}/comments | read: –, write: yes | comments |
| DELETE | /api/posts/{id}/comments/{cid} | yes | comment author or post author |
| POST | /api/blogs | yes | **generate** a post with the agent (202, background); optional `category_id`, otherwise auto-categorised |
| POST | /api/blogs/manual | yes | publish a post you wrote yourself |
| GET | /api/blogs | yes | my posts (all statuses) |
| GET | /api/blogs/{id} | yes | my post + generation progress |
| PATCH | /api/blogs/{id} | yes | **edit** title / markdown / category / is_published |
| DELETE | /api/blogs/{id} | yes | delete post, its comments and its Cloudinary images |
| GET | /api/blogs/{id}/download | yes | Markdown file |

## Notes
- **Image model**: `Comfy-Org/Qwen-Image_ComfyUI` holds ComfyUI-format split weights and is not callable through Hugging Face Inference. The default `HF_IMAGE_MODEL=Qwen/Qwen-Image` is the callable version. Change it (and `HF_IMAGE_PROVIDER`) in `.env` to use another model. If an image fails, the post still saves with the prompt in place of the image.
- **Research**: needs `TAVILY_API_KEY`. Without it, every topic runs closed-book.
- **Image storage**: set the three `CLOUDINARY_*` values and generated images and avatars upload to Cloudinary (folder `draftroom/`), and are removed when a post is deleted. Without them, files go to `backend/static/` for local dev only.
- **Existing database**: `create_all` does not alter tables that already exist. If you ran the previous version, drop the old `users` and `blogs` tables in the Neon SQL editor (`DROP TABLE blogs, users CASCADE;`) and restart so they are recreated with the new columns. Use Alembic from here on.
- **Background jobs**: generation uses FastAPI BackgroundTasks, which dies with the server process. Fine for one worker; use Celery/RQ/Arq if you scale.
- **Production**: set a strong `JWT_SECRET`, set `CORS_ORIGINS` to your frontend URL, and use Alembic for migrations.
