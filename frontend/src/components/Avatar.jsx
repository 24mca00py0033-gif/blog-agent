import { assetUrl } from "../api";

export default function Avatar({ user, size = 36 }) {
  const style = { width: size, height: size, fontSize: size * 0.45 };
  if (user?.avatar_url) return <img className="avatar" style={style} src={assetUrl(user.avatar_url)} alt="" />;
  return <span className="avatar ph" style={style}>{(user?.name || "?").slice(0, 1).toUpperCase()}</span>;
}
