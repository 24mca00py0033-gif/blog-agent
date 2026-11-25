import { createContext, useContext, useEffect, useState, useCallback } from "react";
import api, { tokenStore } from "./api";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(!!tokenStore.get());

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  useEffect(() => {
    if (!tokenStore.get()) return;
    api.get("/api/auth/me").then((r) => setUser(r.data)).catch(logout).finally(() => setLoading(false));
  }, [logout]);

  useEffect(() => {
    window.addEventListener("auth:logout", logout);
    return () => window.removeEventListener("auth:logout", logout);
  }, [logout]);

  const authenticate = async (path, payload) => {
    const { data } = await api.post(path, payload);
    tokenStore.set(data.access_token);
    setUser(data.user);
  };

  const value = {
    user,
    setUser,
    loading,
    login: (email, password) => authenticate("/api/auth/login", { email, password }),
    signup: (name, email, password) => authenticate("/api/auth/signup", { name, email, password }),
    logout,
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
