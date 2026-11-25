"""
Your LangGraph blog writer, adapted for the web app:
  - ChatGroq instead of ChatOpenAI
  - Hugging Face image generation instead of Gemini
  - images saved under static/images/<blog_id>/ and linked with URLs the frontend can load
  - run_blog_agent() streams node updates so the UI can show progress
"""
from __future__ import annotations

import operator
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Annotated, Callable, List, Literal, Optional, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import BaseModel, Field

from ..config import get_settings
from .image_service import generate_image_bytes
from .storage import upload_image


# ---------------- Schemas ----------------
class Task(BaseModel):
    id: int
    title: str
    goal: str = Field(..., description="One sentence describing what the reader should do/understand.")
    bullets: List[str] = Field(..., min_length=3, max_length=6)
    target_words: int = Field(..., description="Target words (120–550).")
    tags: List[str] = Field(default_factory=list)
    requires_research: bool = False
    requires_citations: bool = False
    requires_code: bool = False


class Plan(BaseModel):
    blog_title: str
    audience: str
    tone: str
    blog_kind: Literal["explainer", "tutorial", "news_roundup", "comparison", "system_design"] = "explainer"
    constraints: List[str] = Field(default_factory=list)
    tasks: List[Task]


class EvidenceItem(BaseModel):
    title: str
    url: str
    published_at: Optional[str] = None
    snippet: Optional[str] = None
    source: Optional[str] = None


class RouterDecision(BaseModel):
    needs_research: bool
    mode: Literal["closed_book", "hybrid", "open_book"]
    reason: str
    queries: List[str] = Field(default_factory=list)
    max_results_per_query: int = Field(5)


class EvidencePack(BaseModel):
    evidence: List[EvidenceItem] = Field(default_factory=list)


class ImageSpec(BaseModel):
    placeholder: str = Field(..., description="e.g. [[IMAGE_1]]")
    filename: str = Field(..., description="e.g. qkv_flow.png")
    alt: str
    caption: str
    prompt: str = Field(..., description="Prompt to send to the image model.")
    size: Literal["1024x1024", "1024x1536", "1536x1024"] = "1024x1024"
    quality: Literal["low", "medium", "high"] = "medium"


class GlobalImagePlan(BaseModel):
    md_with_placeholders: str
    images: List[ImageSpec] = Field(default_factory=list)


class State(TypedDict, total=False):
    topic: str
    blog_id: int
    mode: str
    needs_research: bool
    queries: List[str]
    evidence: List[EvidenceItem]
    plan: Optional[Plan]
    as_of: str
    recency_days: int
    sections: Annotated[List[tuple[int, str]], operator.add]
    merged_md: str
    md_with_placeholders: str
    image_specs: List[dict]
    final: str


# ---------------- LLM ----------------
_llm: ChatGroq | None = None


def get_llm() -> ChatGroq:
    global _llm
    if _llm is None:
        s = get_settings()
        if not s.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not set.")
        _llm = ChatGroq(model=s.groq_model, api_key=s.groq_api_key, temperature=0.4)
    return _llm


# ---------------- Router ----------------
ROUTER_SYSTEM = """You are a routing module for a technical blog planner.

Decide whether web research is needed BEFORE planning.

Modes:
- closed_book (needs_research=false): evergreen concepts.
- hybrid (needs_research=true): evergreen + needs up-to-date examples/tools/models.
- open_book (needs_research=true): volatile weekly/news/"latest"/pricing/policy.

If needs_research=true:
- Output 3–10 high-signal, scoped queries.
- For open_book weekly roundup, include queries reflecting last 7 days.
"""


def router_node(state: State) -> dict:
    decision = get_llm().with_structured_output(RouterDecision).invoke(
        [
            SystemMessage(content=ROUTER_SYSTEM),
            HumanMessage(content=f"Topic: {state['topic']}\nAs-of date: {state['as_of']}"),
        ]
    )
    # No Tavily key -> research cannot run, so fall back to closed_book
    if decision.needs_research and not get_settings().tavily_api_key:
        decision.needs_research, decision.mode, decision.queries = False, "closed_book", []

    recency_days = {"open_book": 7, "hybrid": 45}.get(decision.mode, 3650)
    return {
        "needs_research": decision.needs_research,
        "mode": decision.mode,
        "queries": decision.queries,
        "recency_days": recency_days,
    }


def route_next(state: State) -> str:
    return "research" if state["needs_research"] else "orchestrator"


# ---------------- Research (Tavily) ----------------
def _tavily_search(query: str, max_results: int = 5) -> List[dict]:
    key = get_settings().tavily_api_key
    if not key:
        return []
    try:
        from tavily import TavilyClient

        res = TavilyClient(api_key=key).search(query=query, max_results=max_results)
        return [
            {
                "title": r.get("title") or "",
                "url": r.get("url") or "",
                "snippet": r.get("content") or "",
                "published_at": r.get("published_date"),
                "source": None,
            }
            for r in res.get("results", [])
        ]
    except Exception:
        return []


def _iso_to_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except Exception:
        return None


RESEARCH_SYSTEM = """You are a research synthesizer.

Given raw web search results, produce EvidenceItem objects.

Rules:
- Only include items with a non-empty url.
- Prefer relevant + authoritative sources.
- Normalize published_at to ISO YYYY-MM-DD if reliably inferable; else null (do NOT guess).
- Keep snippets short.
- Deduplicate by URL.
"""


def research_node(state: State) -> dict:
    raw: List[dict] = []
    for q in (state.get("queries") or [])[:10]:
        raw.extend(_tavily_search(q, max_results=6))
    if not raw:
        return {"evidence": []}

    pack = get_llm().with_structured_output(EvidencePack).invoke(
        [
            SystemMessage(content=RESEARCH_SYSTEM),
            HumanMessage(
                content=f"As-of date: {state['as_of']}\nRecency days: {state['recency_days']}\n\nRaw results:\n{raw[:40]}"
            ),
        ]
    )
    dedup = {e.url: e for e in pack.evidence if e.url}
    evidence = list(dedup.values())

    if state.get("mode") == "open_book":
        cutoff = date.fromisoformat(state["as_of"]) - timedelta(days=int(state["recency_days"]))
        evidence = [e for e in evidence if (d := _iso_to_date(e.published_at)) and d >= cutoff]
    return {"evidence": evidence}


# ---------------- Orchestrator ----------------
ORCH_SYSTEM = """You are a senior technical writer and developer advocate.
Produce a highly actionable outline for a technical blog post.

Requirements:
- 5–9 tasks, each with goal + 3–6 bullets + target_words.
- Tags are flexible; do not force a fixed taxonomy.

Grounding:
- closed_book: evergreen, no evidence dependence.
- hybrid: use evidence for up-to-date examples; mark those tasks requires_research=True and requires_citations=True.
- open_book: weekly/news roundup:
  - Set blog_kind="news_roundup"
  - No tutorial content unless requested
  - If evidence is weak, plan should explicitly reflect that (don't invent events).

Output must match Plan schema.
"""


def orchestrator_node(state: State) -> dict:
    mode = state.get("mode", "closed_book")
    evidence = state.get("evidence", [])
    forced = "news_roundup" if mode == "open_book" else None

    plan = get_llm().with_structured_output(Plan).invoke(
        [
            SystemMessage(content=ORCH_SYSTEM),
            HumanMessage(
                content=(
                    f"Topic: {state['topic']}\nMode: {mode}\n"
                    f"As-of: {state['as_of']} (recency_days={state['recency_days']})\n"
                    f"{'Force blog_kind=news_roundup' if forced else ''}\n\n"
                    f"Evidence:\n{[e.model_dump() for e in evidence][:16]}"
                )
            ),
        ]
    )
    if forced:
        plan.blog_kind = "news_roundup"
    return {"plan": plan}


def fanout(state: State):
    return [
        Send(
            "worker",
            {
                "task": task.model_dump(),
                "topic": state["topic"],
                "mode": state["mode"],
                "as_of": state["as_of"],
                "recency_days": state["recency_days"],
                "plan": state["plan"].model_dump(),
                "evidence": [e.model_dump() for e in state.get("evidence", [])],
            },
        )
        for task in state["plan"].tasks
    ]


# ---------------- Worker ----------------
WORKER_SYSTEM = """You are a senior technical writer and developer advocate.
Write ONE section of a technical blog post in Markdown.

Constraints:
- Cover ALL bullets in order.
- Target words ±15%.
- Output only section markdown starting with "## <Section Title>".

Scope guard:
- If blog_kind=="news_roundup", do NOT drift into tutorials (scraping/RSS/how to fetch).
  Focus on events + implications.

Grounding:
- If mode=="open_book": do not introduce any specific event/company/model/funding/policy claim unless supported by provided Evidence URLs.
  For each supported claim, attach a Markdown link ([Source](URL)).
  If unsupported, write "Not found in provided sources."
- If requires_citations==true (hybrid tasks): cite Evidence URLs for external claims.

Code:
- If requires_code==true, include at least one minimal snippet.
"""


def worker_node(payload: dict) -> dict:
    task = Task(**payload["task"])
    plan = Plan(**payload["plan"])
    evidence = [EvidenceItem(**e) for e in payload.get("evidence", [])]
    bullets_text = "\n- " + "\n- ".join(task.bullets)
    evidence_text = "\n".join(f"- {e.title} | {e.url} | {e.published_at or 'date:unknown'}" for e in evidence[:20])

    section_md = get_llm().invoke(
        [
            SystemMessage(content=WORKER_SYSTEM),
            HumanMessage(
                content=(
                    f"Blog title: {plan.blog_title}\nAudience: {plan.audience}\nTone: {plan.tone}\n"
                    f"Blog kind: {plan.blog_kind}\nConstraints: {plan.constraints}\n"
                    f"Topic: {payload['topic']}\nMode: {payload.get('mode')}\n"
                    f"As-of: {payload.get('as_of')} (recency_days={payload.get('recency_days')})\n\n"
                    f"Section title: {task.title}\nGoal: {task.goal}\nTarget words: {task.target_words}\n"
                    f"Tags: {task.tags}\nrequires_research: {task.requires_research}\n"
                    f"requires_citations: {task.requires_citations}\nrequires_code: {task.requires_code}\n"
                    f"Bullets:{bullets_text}\n\nEvidence (ONLY cite these URLs):\n{evidence_text}\n"
                )
            ),
        ]
    ).content.strip()
    return {"sections": [(task.id, section_md)]}


# ---------------- Reducer with images ----------------
def merge_content(state: State) -> dict:
    plan = state["plan"]
    ordered = [md for _, md in sorted(state["sections"], key=lambda x: x[0])]
    body = "\n\n".join(ordered).strip()
    return {"merged_md": f"# {plan.blog_title}\n\n{body}\n"}


DECIDE_IMAGES_SYSTEM = """You are an expert technical editor.
Decide if images/diagrams are needed for THIS blog.

Rules:
- Max 3 images total.
- Each image must materially improve understanding (diagram/flow/table-like visual).
- Insert placeholders exactly: [[IMAGE_1]], [[IMAGE_2]], [[IMAGE_3]].
- If no images needed: md_with_placeholders must equal input and images=[].
- Avoid decorative images; prefer technical diagrams with short labels.
Return strictly GlobalImagePlan.
"""


def decide_images(state: State) -> dict:
    plan = state["plan"]
    image_plan = get_llm().with_structured_output(GlobalImagePlan).invoke(
        [
            SystemMessage(content=DECIDE_IMAGES_SYSTEM),
            HumanMessage(
                content=(
                    f"Blog kind: {plan.blog_kind}\nTopic: {state['topic']}\n\n"
                    f"Insert placeholders + propose image prompts.\n\n{state['merged_md']}"
                )
            ),
        ]
    )
    return {
        "md_with_placeholders": image_plan.md_with_placeholders,
        "image_specs": [img.model_dump() for img in image_plan.images],
    }


def _safe_filename(name: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", Path(name).stem).strip("_") or "image"
    return f"{stem}.png"


def generate_and_place_images(state: State) -> dict:
    md = state.get("md_with_placeholders") or state["merged_md"]
    specs = state.get("image_specs", []) or []
    folder = f"draftroom/blog_{state['blog_id']}"

    for spec in specs:
        placeholder = spec["placeholder"]
        public_id = Path(_safe_filename(spec["filename"])).stem
        try:
            data = generate_image_bytes(spec["prompt"], spec.get("size", "1024x1024"))
            url = upload_image(data, folder, public_id)  # Cloudinary URL (or /static/... locally)
            md = md.replace(placeholder, f"![{spec['alt']}]({url})\n*{spec['caption']}*")
        except Exception as e:  # keep the post usable if one image fails
            fallback = (
                f"> **[Image could not be generated]** {spec.get('caption', '')}\n>\n"
                f"> Prompt: {spec.get('prompt', '')}\n>\n> Error: {e}\n"
            )
            md = md.replace(placeholder, fallback)
    return {"final": md}


reducer_graph = StateGraph(State)
reducer_graph.add_node("merge_content", merge_content)
reducer_graph.add_node("decide_images", decide_images)
reducer_graph.add_node("generate_and_place_images", generate_and_place_images)
reducer_graph.add_edge(START, "merge_content")
reducer_graph.add_edge("merge_content", "decide_images")
reducer_graph.add_edge("decide_images", "generate_and_place_images")
reducer_graph.add_edge("generate_and_place_images", END)
reducer_subgraph = reducer_graph.compile()

g = StateGraph(State)
g.add_node("router", router_node)
g.add_node("research", research_node)
g.add_node("orchestrator", orchestrator_node)
g.add_node("worker", worker_node)
g.add_node("reducer", reducer_subgraph)
g.add_edge(START, "router")
g.add_conditional_edges("router", route_next, {"research": "research", "orchestrator": "orchestrator"})
g.add_edge("research", "orchestrator")
g.add_conditional_edges("orchestrator", fanout, ["worker"])
g.add_edge("worker", "reducer")
g.add_edge("reducer", END)
graph_app = g.compile()


# ---------------- Public entry point ----------------
def run_blog_agent(topic: str, blog_id: int, on_step: Callable[[str], None]) -> dict:
    init: State = {
        "topic": topic,
        "blog_id": blog_id,
        "as_of": date.today().isoformat(),
        "recency_days": 7,
        "mode": "",
        "needs_research": False,
        "queries": [],
        "evidence": [],
        "plan": None,
        "sections": [],
    }
    on_step("Deciding whether research is needed")
    plan: Plan | None = None
    mode, evidence, final = "closed_book", [], ""
    done_workers = 0

    for update in graph_app.stream(init, stream_mode="updates"):
        for node, out in update.items():
            out = out or {}
            if node == "router":
                mode = out.get("mode", mode)
                on_step("Researching the web" if out.get("needs_research") else "Planning the outline")
            elif node == "research":
                evidence = out.get("evidence", [])
                on_step("Planning the outline")
            elif node == "orchestrator":
                plan = out["plan"]
                on_step(f"Writing sections (0/{len(plan.tasks)})")
            elif node == "worker":
                done_workers += 1
                total = len(plan.tasks) if plan else done_workers
                on_step(f"Writing sections ({done_workers}/{total})")
                if done_workers >= total:
                    on_step("Merging sections and generating images")
            elif node == "reducer":
                final = out.get("final", "")

    if not plan or not final:
        raise RuntimeError("The agent finished without producing a blog post.")
    return {
        "title": plan.blog_title,
        "markdown": final,
        "mode": mode,
        "plan": plan.model_dump(),
        "evidence": [e.model_dump() for e in evidence],
    }


# ---------------- Category classifier ----------------
class CategoryChoice(BaseModel):
    category: str


def classify_category(title: str, topic: str, names: List[str]) -> str:
    """Pick one of `names` for the post; falls back to 'Other'."""
    try:
        choice = get_llm().with_structured_output(CategoryChoice).invoke(
            [
                SystemMessage(content="Pick the single best category for this blog post. Answer with exactly one of: " + ", ".join(names)),
                HumanMessage(content=f"Title: {title}\nTopic: {topic}"),
            ]
        )
        return choice.category if choice.category in names else "Other"
    except Exception:
        return "Other"
