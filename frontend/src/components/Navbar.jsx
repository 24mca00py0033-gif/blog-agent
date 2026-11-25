import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import Avatar from "./Avatar";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <header className="nav">
      <Link to="/" className="brand">Draftroom</Link>
      <nav>
        {user ? (
          <>
            <Link to="/dashboard" className="btn">New post</Link>
            <Link to="/dashboard">My posts</Link>
            <Link to={`/u/${user.id}`} className="navuser"><Avatar user={user} size={28} />{user.name}</Link>
            <Link to="/settings">Settings</Link>
            <button className="btn ghost" onClick={() => { logout(); navigate("/"); }}>Log out</button>
          </>
        ) : (
          <>
            <Link to="/login">Log in</Link>
            <Link to="/signup" className="btn">Sign up</Link>
          </>
        )}
      </nav>
    </header>
  );
}
