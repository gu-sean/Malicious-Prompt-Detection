/**
 * AuthContext - JWT-based authentication context
 * Design: Obsidian Precision - Dark tech SaaS
 * Connects to the real backend APIs (/api/users/login, /api/users/signup).
 */

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface User {
  id: string;
  email: string;
  name: string;
  plan: 'free' | 'pro' | 'enterprise';
  createdAt: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

function parseToken(token: string): User | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1]));
    
    // JWT exp is in seconds
    if (payload.exp && payload.exp * 1000 < Date.now()) return null;
    
    // Fallbacks for name and id since they might not be fully provided by the backend JWT payload
    const email = payload.sub || '';
    const name = email.split('@')[0] || 'User';
    
    return {
      id: payload.user_id ? String(payload.user_id) : 'unknown',
      email: email,
      name: name,
      plan: 'free',
      createdAt: new Date().toISOString(), // Or from payload if available
    };
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedToken = localStorage.getItem('pg_token');
    if (storedToken) {
      const parsedUser = parseToken(storedToken);
      if (parsedUser) {
        setUser(parsedUser);
        setToken(storedToken);
      } else {
        localStorage.removeItem('pg_token');
      }
    }
    setIsLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    const response = await fetch('/api/users/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      let errorMessage = '이메일 또는 비밀번호가 올바르지 않습니다.';
      try {
        const errorData = await response.json();
        // If the backend returns a detail string, we can use it or fallback to Korean.
        // We stick to the default Korean for a better UX if backend error is generic.
        if (errorData.detail && errorData.detail !== 'Invalid credentials') {
          errorMessage = errorData.detail;
        }
      } catch (e) {
        // Fallback error message
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();
    const newToken = data.access_token;
    if (!newToken) throw new Error('토큰을 발급받지 못했습니다.');

    const parsedUser = parseToken(newToken);
    if (!parsedUser) throw new Error('유효하지 않은 토큰입니다.');

    localStorage.setItem('pg_token', newToken);
    setToken(newToken);
    setUser(parsedUser);
  };

  const register = async (name: string, email: string, password: string) => {
    const response = await fetch('/api/users/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      let errorMessage = '회원가입에 실패했습니다.';
      try {
        const errorData = await response.json();
        if (errorData.detail) errorMessage = errorData.detail;
      } catch (e) {
        // Fallback error message
      }
      throw new Error(errorMessage);
    }

    // After successful signup, auto login
    await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem('pg_token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        register,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
