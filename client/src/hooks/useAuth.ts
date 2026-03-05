import { useState, useEffect, useCallback } from "react";

const JWT_KEY = "aic_jwt";

interface AuthUser {
  email: string;
  name: string;
  dealership: string;
  phone: string;
}

interface UseAuthReturn {
  user: AuthUser | null;
  jwt: string;
  isLoggedIn: boolean;
  login: (jwt: string) => void;
  logout: () => void;
}

function decodePayload(token: string): AuthUser | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1]));
    // Check expiry
    if (payload.exp && payload.exp * 1000 < Date.now()) return null;
    return {
      email: payload.sub,
      name: payload.name,
      dealership: payload.dealership,
      phone: payload.phone || "",
    };
  } catch {
    return null;
  }
}

export function useAuth(): UseAuthReturn {
  const [jwt, setJwt] = useState("");
  const [user, setUser] = useState<AuthUser | null>(null);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(JWT_KEY);
      if (stored) {
        const decoded = decodePayload(stored);
        if (decoded) {
          setJwt(stored);
          setUser(decoded);
        } else {
          // Expired or invalid — clear it
          localStorage.removeItem(JWT_KEY);
        }
      }
    } catch {
      // localStorage unavailable
    }
  }, []);

  const login = useCallback((token: string) => {
    const decoded = decodePayload(token);
    if (decoded) {
      setJwt(token);
      setUser(decoded);
      try {
        localStorage.setItem(JWT_KEY, token);
      } catch {
        // localStorage unavailable
      }
    }
  }, []);

  const logout = useCallback(() => {
    setJwt("");
    setUser(null);
    try {
      localStorage.removeItem(JWT_KEY);
    } catch {
      // localStorage unavailable
    }
  }, []);

  return {
    user,
    jwt,
    isLoggedIn: !!user,
    login,
    logout,
  };
}
