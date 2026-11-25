import { Routes, Route, Navigate } from "react-router-dom";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import BlogView from "./pages/BlogView";
import PostView from "./pages/PostView";
import Editor from "./pages/Editor";
import Profile from "./pages/Profile";
import Settings from "./pages/Settings";

const guard = (el) => <ProtectedRoute>{el}</ProtectedRoute>;

export default function App() {
  return (
    <>
      <Navbar />
      <main className="page">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/posts/:id" element={<PostView />} />
          <Route path="/u/:id" element={<Profile />} />
          <Route path="/dashboard" element={guard(<Dashboard />)} />
          <Route path="/blogs/:id" element={guard(<BlogView />)} />
          <Route path="/write" element={guard(<Editor />)} />
          <Route path="/posts/:id/edit" element={guard(<Editor />)} />
          <Route path="/settings" element={guard(<Settings />)} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}
