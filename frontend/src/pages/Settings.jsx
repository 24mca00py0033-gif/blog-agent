import { useState } from "react";
import api, { errorMessage } from "../api";
import { useAuth } from "../auth";
import Avatar from "../components/Avatar";

export default function Settings() {
  const { user, setUser } = useAuth();
  const [name, setName] = useState(user.name);
  const [bio, setBio] = useState(user.bio || "");
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const save = async (e) => {
    e.preventDefault();
    setBusy(true); setError(""); setMsg("");
    try {
      const { data } = await api.patch("/api/users/me", { name, bio });
      setUser(data);
      setMsg("Profile saved.");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true); setError(""); setMsg("");
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await api.post("/api/users/me/avatar", fd);
      setUser(data);
      setMsg("Photo updated.");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  };

  return (
    <form className="card auth" onSubmit={save} style={{ maxWidth: 520 }}>
      <h2>Profile settings</h2>
      <div className="avatar-row">
        <Avatar user={user} size={72} />
        <label className="btn ghost filebtn">
          Change photo
          <input type="file" accept="image/png,image/jpeg,image/webp" onChange={upload} hidden />
        </label>
      </div>
      <label>Name<input value={name} onChange={(e) => setName(e.target.value)} required maxLength={120} /></label>
      <label>Bio<textarea rows={4} value={bio} onChange={(e) => setBio(e.target.value)} maxLength={500} placeholder="A sentence or two about you" /></label>
      <small className="muted">Email: {user.email}</small>
      {error && <p className="error">{error}</p>}
      {msg && <p className="ok">{msg}</p>}
      <button className="btn" disabled={busy}>{busy ? "Saving…" : "Save profile"}</button>
    </form>
  );
}
