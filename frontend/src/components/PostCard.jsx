import { Link } from "react-router-dom";
import { assetUrl, fmtDate } from "../api";

export default function PostCard({ post }) {
  const href = `/posts/${post.id}`;
  return (
    <article className="pcard">
      <Link to={href} className="pcard-cover" aria-hidden="true" tabIndex={-1}>
        {post.cover_url ? <img src={assetUrl(post.cover_url)} alt="" loading="lazy" /> : <div className="pcard-ph">{post.title.slice(0, 1)}</div>}
      </Link>
      <div className="pcard-body">
        {post.category && <Link to={`/?category=${post.category.slug}`} className="tag">{post.category.name}</Link>}
        <h3><Link to={href}>{post.title}</Link></h3>
        {post.excerpt && <p className="muted">{post.excerpt}</p>}
        <div className="meta">
          <Link to={`/u/${post.author.id}`}>{post.author.name}</Link>
          <span>{fmtDate(post.created_at)}</span>
          <span>{post.comment_count} {post.comment_count === 1 ? "comment" : "comments"}</span>
        </div>
      </div>
    </article>
  );
}
