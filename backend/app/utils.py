import re

_IMG = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")


def make_excerpt(md: str, limit: int = 200) -> str:
    t = re.sub(r"```.*?```", " ", md, flags=re.S)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"^#+\s.*$", " ", t, flags=re.M)
    t = re.sub(r"[*_`>#|\-]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= limit else t[: limit - 1].rstrip() + "…"


def first_image_url(md: str) -> str:
    m = _IMG.search(md)
    return m.group(1) if m else ""


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
