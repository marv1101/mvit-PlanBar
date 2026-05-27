import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../lib/api';
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from '../lib/auth';
import { changePassword as changePasswordApi } from '../services/userService';

interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'employee';
  employeeId?: string;
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<{ success: boolean; mustChangePassword: boolean }>;
  logout: () => void;
  isLoading: boolean;
  mustChangePassword: boolean;
  changePassword: (oldPassword: string, newPassword: string) => Promise<boolean>;
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
  const [mustChangePassword, setMustChangePassword] = useState(false);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setIsLoading(false);
      return;
    }
    api.get('/users/me')
      .then(res => {
        setUser(mapBackendUser(res.data));
        if (res.data.must_change_password) {
          setMustChangePassword(true);
        }
      })
      .catch(() => clearTokens())
      .finally(() => setIsLoading(false));
  }, []);

  const login = async (email: string, password: string): Promise<{ success: boolean; mustChangePassword: boolean }> => {
    try {
      const { data } = await api.post('/users/login', { email, password });
      setTokens(data.access_token, data.refresh_token);
      const me = await api.get('/users/me');
      setUser(mapBackendUser(me.data));
      const mustChange = data.must_change_password ?? me.data.must_change_password ?? false;
      setMustChangePassword(mustChange);
      return { success: true, mustChangePassword: mustChange };
    } catch {
      return { success: false, mustChangePassword: false };
    }
  };

  const handleChangePassword = async (oldPassword: string, newPassword: string): Promise<boolean> => {
    try {
      await changePasswordApi(oldPassword, newPassword);
      setMustChangePassword(false);
      return true;
    } catch {
      return false;
    }
  };

  const logout = () => {
    setUser(null);
    setMustChangePassword(false);
    clearTokens();
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, isLoading, mustChangePassword, changePassword: handleChangePassword }}>
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
