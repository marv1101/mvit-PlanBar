import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../lib/api';
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from '../lib/auth';

interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'employee';
  employeeId?: string;
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function mapBackendUser(data: { id: number; username: string; email: string; role: string }): User {
  return {
    id: String(data.id),
    name: data.username,
    email: data.email,
    role: data.role === 'user' ? 'employee' : (data.role as 'admin' | 'employee'),
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setIsLoading(false);
      return;
    }
    api.get('/users/me')
      .then(res => setUser(mapBackendUser(res.data)))
      .catch(() => clearTokens())
      .finally(() => setIsLoading(false));
  }, []);

  const login = async (email: string, password: string): Promise<boolean> => {
    try {
      const { data } = await api.post('/users/login', { email, password });
      setTokens(data.access_token, data.refresh_token);
      const me = await api.get('/users/me');
      setUser(mapBackendUser(me.data));
      return true;
    } catch {
      return false;
    }
  };

  const logout = () => {
    setUser(null);
    clearTokens();
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
