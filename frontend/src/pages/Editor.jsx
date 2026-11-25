import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import api, { assetUrl, errorMessage } from "../api";

// Used for both "/write" (new, manual) and "/posts/:id/edit".
export default function Editor() {
  const { id } = useParams();
  const editing = !!id;
  const navigate = useNavigate();
  const [categories, setCategories] = useState([]);
  const [form, setForm] = useState({ title: "", markdown: "", category_id: "", is_published: true });
  const [preview, setPreview] = useState(false);
  const [loading, setLoading] = useState(editing);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { api.get("/api/categories").then((r) => setCategories(r.data)); }, []);

  useEffect(() => {
    if (!editing) return;
    api.get(`/api/blogs/${id}`)
      .then(({ data }) => setForm({ title: data.title, markdown: data.markdown, category_id: data.category?.id ?? "", is_published: data.is_published }))
      .catch((e) => setError(errorMessage(e)))
      .finally(() => setLoading(false));
  }, [id, editing]);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    const payload = { ...form, category_id: form.category_id === "" ? null : Number(form.category_id) };
    try {
      const { data } = editing ? await api.patch(`/api/blogs/${id}`, payload) : await api.post("/api/blogs/manual", payload);
      navigate(`/posts/${data.id}`);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  };

  if (loading) return <p className="muted">Loading…</p>;

  return (
    <form className="card editor" onSubmit={save}>
      <h2>{editing ? "Edit post" : "Write a post"}</h2>
      <label>Title<input value={form.title} onChange={set("title")} required maxLength={300} /></label>
      <label>
        Category
        <select value={form.category_id} onChange={set("category_id")}>
          <option value="">None</option>
          {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </label>
      <div className="tabs">
        <button type="button" className={`chip ${!preview ? "on" : ""}`} onClick={() => setPreview(false)}>Markdown</button>
        <button type="button" className={`chip ${preview ? "on" : ""}`} onClick={() => setPreview(true)}>Preview</button>
      </div>
      {preview ? (
        <article className="prose">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ img: ({ src, alt }) => <img src={assetUrl(src)} alt={alt} /> }}>
            {form.markdown || "*Nothing to preview yet.*"}
          </ReactMarkdown>
        </article>
      ) : (
        <textarea className="mono" rows={24} value={form.markdown} onChange={set("markdown")} required />
      )}
      <label className="check"><input type="checkbox" checked={form.is_published} onChange={set("is_published")} /> Show on the home page</label>
      {error && <p className="error">{error}</p>}
      <div className="toolbar">
        <button className="btn" disabled={busy}>{busy ? "Saving…" : editing ? "Save changes" : "Publish"}</button>
        <Link to={editing ? `/posts/${id}` : "/dashboard"} className="btn ghost">Cancel</Link>
      </div>
    </form>
  );
}
