import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import api, { errorMessage } from "../api";

// Progress screen shown while the agent writes. Redirects to the post when done.
export default function BlogView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [blog, setBlog] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let timer;
    let cancelled = false;
    const poll = async () => {
      try {
        const { data } = await api.get(`/api/blogs/${id}`);
        if (cancelled) return;
        if (data.status === "completed") return navigate(`/posts/${id}`, { replace: true });
        setBlog(data);
        if (data.status === "pending" || data.status === "running") timer = setTimeout(poll, 2500);
      } catch (err) {
        if (!cancelled) setError(errorMessage(err));
      }
    };
    poll();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [id, navigate]);

  const remove = async () => {
    await api.delete(`/api/blogs/${id}`);
    navigate("/dashboard");
  };

  if (error) return <p className="error">{error} <Link to="/dashboard">Back to my posts</Link></p>;
  if (!blog) return <p className="muted">Loading…</p>;

  if (blog.status === "failed") {
    return (
      <div className="card">
        <h2>Generation failed</h2>
        <p className="error">{blog.error || "Unknown error"}</p>
        <div className="toolbar">
          <Link to="/dashboard" className="btn">Back to my posts</Link>
          <button className="btn ghost" onClick={remove}>Delete</button>
        </div>
      </div>
    );
  }

  return (
    <div className="card center-text">
      <h2>Writing your post</h2>
      <p className="muted">{blog.topic}</p>
      <div className="bar"><div /></div>
      <p>{blog.progress}…</p>
      <p className="muted">This usually takes a minute or two. You can leave this page; the post will appear in My posts.</p>
    </div>
  );
}
