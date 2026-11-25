import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api, { errorMessage, fmtDate } from "../api";
import { useAuth } from "../auth";
import Avatar from "../components/Avatar";
import PostCard from "../components/PostCard";

export default function Profile() {
  const { id } = useParams();
  const { user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [posts, setPosts] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    setProfile(null);
    api.get(`/api/users/${id}`).then((r) => setProfile(r.data)).catch((e) => setError(errorMessage(e)));
    api.get("/api/posts", { params: { author_id: id, limit: 60 } }).then((r) => setPosts(r.data.items));
  }, [id]);

  if (error) return <p className="error">{error}</p>;
  if (!profile) return <p className="muted">Loading…</p>;

  return (
    <>
      <section className="profile">
        <Avatar user={profile} size={88} />
        <div>
          <h1>{profile.name}</h1>
          {profile.bio && <p>{profile.bio}</p>}
          <p className="muted">{profile.post_count} {profile.post_count === 1 ? "post" : "posts"} · Joined {fmtDate(profile.created_at)}</p>
          {user?.id === profile.id && <Link to="/settings" className="btn ghost">Edit profile</Link>}
        </div>
      </section>
      {posts.length === 0 ? <p className="muted">No published posts yet.</p> : <div className="grid">{posts.map((p) => <PostCard key={p.id} post={p} />)}</div>}
    </>
  );
}
