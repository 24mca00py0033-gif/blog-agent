import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api, { errorMessage } from "../api";
import { useAuth } from "../auth";
import PostCard from "../components/PostCard";

export default function Home() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const slug = params.get("category") || "";
  const q = params.get("q") || "";
  const filtered = !!(slug || q);

  const [categories, setCategories] = useState([]);
  const [search, setSearch] = useState(q);
  const [posts, setPosts] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => { api.get("/api/categories").then((r) => setCategories(r.data)).catch(() => {}); }, []);
  useEffect(() => setSearch(q), [q]);

  useEffect(() => {
    setLoading(true);
    setError("");
    api
      .get("/api/posts", { params: { category: slug || undefined, q: q || undefined, limit: filtered ? 12 : 60 } })
      .then((r) => { setPosts(r.data.items); setTotal(r.data.total); })
      .catch((e) => setError(errorMessage(e)))
      .finally(() => setLoading(false));
  }, [slug, q, filtered]);

  const loadMore = async () => {
    const { data } = await api.get("/api/posts", { params: { category: slug || undefined, q: q || undefined, limit: 12, offset: posts.length } });
    setPosts((p) => [...p, ...data.items]);
  };

  const setFilter = (next) => {
    const p = new URLSearchParams();
    if (next.category) p.set("category", next.category);
    if (next.q) p.set("q", next.q);
    setParams(p);
  };

  // "All" view: one section per category, in category order
  const groups = useMemo(() => {
    const map = new Map();
    for (const c of categories) map.set(c.name, { cat: c, items: [] });
    for (const p of posts) {
      const key = p.category?.name || "Other";
      if (!map.has(key)) map.set(key, { cat: p.category, items: [] });
      map.get(key).items.push(p);
    }
    return [...map.values()].filter((g) => g.items.length);
  }, [posts, categories]);

  return (
    <>
      {!user && (
        <section className="hero">
          <h1>Technical posts written by people and their AI drafting agent.</h1>
          <p className="lead">Browse by topic below, or sign up and give Draftroom a topic to get a researched, illustrated post of your own.</p>
          <Link to="/signup" className="btn big">Create a free account</Link>
        </section>
      )}

      <form className="searchbar" onSubmit={(e) => { e.preventDefault(); setFilter({ category: slug, q: search.trim() }); }}>
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search posts" aria-label="Search posts" />
        <button className="btn">Search</button>
      </form>

      <nav className="chips" aria-label="Categories">
        <button className={`chip ${!slug ? "on" : ""}`} onClick={() => setFilter({ q })}>All</button>
        {categories.map((c) => (
          <button key={c.id} className={`chip ${slug === c.slug ? "on" : ""}`} onClick={() => setFilter({ category: c.slug, q })}>{c.name}</button>
        ))}
      </nav>

      {error && <p className="error">{error}</p>}
      {loading ? (
        <p className="muted">Loading posts…</p>
      ) : posts.length === 0 ? (
        <p className="muted">{filtered ? "No posts match that filter." : "No posts yet. Be the first to write one."}</p>
      ) : filtered ? (
        <>
          <div className="grid">{posts.map((p) => <PostCard key={p.id} post={p} />)}</div>
          {posts.length < total && <button className="btn ghost more" onClick={loadMore}>Load more</button>}
        </>
      ) : (
        groups.map(({ cat, items }) => (
          <section key={cat?.id || "other"} className="group">
            <h2>{cat ? <a href={`/?category=${cat.slug}`} onClick={(e) => { e.preventDefault(); setFilter({ category: cat.slug }); }}>{cat.name}</a> : "Other"}</h2>
            <div className="grid">{items.slice(0, 6).map((p) => <PostCard key={p.id} post={p} />)}</div>
          </section>
        ))
      )}
    </>
  );
}
