import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage, fmtDate } from "../api";
import { useAuth } from "../auth";
import Avatar from "./Avatar";

export default function Comments({ postId, postAuthorId, onCountChange }) {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [body, setBody] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get(`/api/posts/${postId}/comments`).then((r) => setItems(r.data)).catch((e) => setError(errorMessage(e)));
  }, [postId]);

  useEffect(() => { onCountChange?.(items.length); }, [items.length]); // eslint-disable-line

  const add = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post(`/api/posts/${postId}/comments`, { body });
      setItems((c) => [...c, data]);
      setBody("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id) => {
    if (!confirm("Delete this comment?")) return;
    try {
      await api.delete(`/api/posts/${postId}/comments/${id}`);
      setItems((c) => c.filter((x) => x.id !== id));
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <section className="comments">
      <h2>Comments ({items.length})</h2>
      {user ? (
        <form onSubmit={add} className="comment-form">
          <textarea rows={3} value={body} onChange={(e) => setBody(e.target.value)} placeholder="Add a comment" maxLength={2000} required />
          <button className="btn" disabled={busy || !body.trim()}>{busy ? "Posting…" : "Post comment"}</button>
        </form>
      ) : (
        <p className="muted"><Link to="/login">Log in</Link> to comment.</p>
      )}
      {error && <p className="error">{error}</p>}
      {items.length === 0 && <p className="muted">No comments yet.</p>}
      <ul className="clist">
        {items.map((c) => (
          <li key={c.id}>
            <Avatar user={c.author} size={32} />
            <div className="cbody">
              <div className="meta">
                <Link to={`/u/${c.author.id}`}><strong>{c.author.name}</strong></Link>
                <span>{fmtDate(c.created_at)}</span>
                {user && (user.id === c.author.id || user.id === postAuthorId) && (
                  <button className="link-btn" onClick={() => remove(c.id)}>Delete</button>
                )}
              </div>
              <p>{c.body}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
