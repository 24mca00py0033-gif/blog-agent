import { useEffect, useState, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import api, { errorMessage, fmtDate } from "../api";

export default function Dashboard() {
  const navigate = useNavigate();
  const [topic, setTopic] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [categories, setCategories] = useState([]);
  const [blogs, setBlogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.get("/api/blogs").then((r) => setBlogs(r.data)).catch((e) => setError(errorMessage(e))).finally(() => setLoading(false));
  }, []);
  useEffect(load, [load]);
  useEffect(() => { api.get("/api/categories").then((r) => setCategories(r.data)); }, []);

  const active = blogs.some((b) => b.status === "pending" || b.status === "running");
  useEffect(() => {
    if (!active) return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [active, load]);

  const create = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const { data } = await api.post("/api/blogs", { topic, category_id: categoryId ? Number(categoryId) : null });
      navigate(`/blogs/${data.id}`);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  };

  const remove = async (id) => {
    if (!confirm("Delete this post and its comments? This can't be undone.")) return;
    await api.delete(`/api/blogs/${id}`);
    setBlogs((b) => b.filter((x) => x.id !== id));
  };

  const togglePublish = async (b) => {
    const { data } = await api.patch(`/api/blogs/${b.id}`, { is_published: !b.is_published });
    setBlogs((list) => list.map((x) => (x.id === b.id ? { ...x, is_published: data.is_published } : x)));
  };

  return (
    <>
      <form className="card composer" onSubmit={create}>
        <h2>What should the post be about?</h2>
        <textarea
          rows={3}
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. How self-attention works in transformers, or: Weekly roundup of open-source LLM releases"
          required minLength={3} maxLength={500}
        />
        <div className="composer-row">
          <label>
            Category
            <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
              <option value="">Choose automatically</option>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </label>
          <button className="btn" disabled={busy}>{busy ? "Starting…" : "Generate post"}</button>
          <Link to="/write" className="btn ghost">Write one yourself</Link>
        </div>
        {error && <p className="error">{error}</p>}
      </form>

      <h2 className="section-title">My posts</h2>
      {loading ? (
        <p className="muted">Loading…</p>
      ) : blogs.length === 0 ? (
        <p className="muted">Nothing here yet. Enter a topic above to write your first post.</p>
      ) : (
        <ul className="list">
          {blogs.map((b) => {
            const working = b.status === "pending" || b.status === "running";
            return (
              <li key={b.id} className="row">
                <Link to={b.status === "completed" ? `/posts/${b.id}` : `/blogs/${b.id}`} className="row-main">
                  <strong>{b.title || b.topic}</strong>
                  <span className="muted">{fmtDate(b.created_at)}{b.category ? ` · ${b.category.name}` : ""}</span>
                </Link>
                <span className={`pill ${b.status}`}>{working ? b.progress : b.status === "completed" ? (b.is_published ? "published" : "draft") : b.status}</span>
                {b.status === "completed" && (
                  <>
                    <button className="btn ghost" onClick={() => togglePublish(b)}>{b.is_published ? "Unpublish" : "Publish"}</button>
                    <Link to={`/posts/${b.id}/edit`} className="btn ghost">Edit</Link>
                  </>
                )}
                <button className="btn ghost" onClick={() => remove(b.id)}>Delete</button>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}
