import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import api, { assetUrl, errorMessage, fmtDate } from "../api";
import { useAuth } from "../auth";
import Avatar from "../components/Avatar";
import Comments from "../components/Comments";

export default function PostView() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [post, setPost] = useState(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setPost(null);
    api.get(`/api/posts/${id}`).then((r) => setPost(r.data)).catch((e) => setError(errorMessage(e)));
  }, [id, user?.id]);

  if (error) return <p className="error">{error} <Link to="/">Back to home</Link></p>;
  if (!post) return <p className="muted">Loading…</p>;

  const isOwner = user?.id === post.author.id;

  const remove = async () => {
    if (!confirm("Delete this post and all its comments? This can't be undone.")) return;
    await api.delete(`/api/blogs/${post.id}`);
    navigate("/dashboard");
  };

  const copy = async () => {
    await navigator.clipboard.writeText(post.markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <>
      <div className="toolbar">
        <Link to="/">← All posts</Link>
        <div>
          <button className="btn ghost" onClick={copy}>{copied ? "Copied" : "Copy Markdown"}</button>
          {isOwner && (
            <>
              <Link to={`/posts/${post.id}/edit`} className="btn ghost">Edit</Link>
              <button className="btn ghost" onClick={remove}>Delete</button>
            </>
          )}
        </div>
      </div>

      <div className="byline">
        <Avatar user={post.author} size={40} />
        <div>
          <Link to={`/u/${post.author.id}`}><strong>{post.author.name}</strong></Link>
          <div className="muted">
            {fmtDate(post.created_at)}
            {post.category && <> · <Link to={`/?category=${post.category.slug}`}>{post.category.name}</Link></>}
            {!post.is_published && <> · <strong>Draft (only you can see this)</strong></>}
          </div>
        </div>
      </div>

      <article className="prose">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            img: ({ src, alt }) => <img src={assetUrl(src)} alt={alt} loading="lazy" />,
            a: ({ href, children }) => <a href={href} target="_blank" rel="noreferrer">{children}</a>,
          }}
        >
          {post.markdown}
        </ReactMarkdown>
      </article>

      <Comments postId={post.id} postAuthorId={post.author.id} />
    </>
  );
}
