import axios from 'axios';
import React, { createContext, useContext, useState, useEffect } from 'react';
import { toast } from 'sonner';
import api from '../lib/api';
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

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

function mapBackendUser(data: { id: number; username: string; email: string; role: string; employee_id?: number | null }): User {
  return {
    id: String(data.id),
    name: data.username,
    email: data.email,
    role: data.role === 'user' ? 'employee' : (data.role as 'admin' | 'employee'),
    employeeId: data.employee_id ? String(data.employee_id) : undefined,
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [mustChangePassword, setMustChangePassword] = useState(false);

  useEffect(() => {
    axios.get('/api/v1/users/me', { withCredentials: true })
      .then(res => {
        setUser(mapBackendUser(res.data));
        if (res.data.must_change_password) {
          setMustChangePassword(true);
        }
      })
      .catch((err) => {
        if (import.meta.env.DEV) console.error('[Auth] /users/me failed:', err);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = async (email: string, password: string): Promise<{ success: boolean; mustChangePassword: boolean }> => {
    try {
      const { data } = await api.post('/users/login', { email, password });
      const me = await api.get('/users/me');
      setUser(mapBackendUser(me.data));
      const mustChange = data.must_change_password ?? me.data.must_change_password ?? false;
      setMustChangePassword(mustChange);
      return { success: true, mustChangePassword: mustChange };
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? err.response?.data?.detail || 'Login fehlgeschlagen'
        : 'Netzwerkfehler';
      toast.error(msg);
      return { success: false, mustChangePassword: false };
    }
  };

  const handleChangePassword = async (oldPassword: string, newPassword: string): Promise<boolean> => {
    try {
      await changePasswordApi(oldPassword, newPassword);
      setMustChangePassword(false);
      return true;
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? err.response?.data?.detail || 'Passwort ändern fehlgeschlagen'
        : 'Netzwerkfehler';
      toast.error(msg);
      return false;
    }
  };

  const logout = () => {
    setUser(null);
    setMustChangePassword(false);
    api.post('/users/logout').catch((err) => {
      if (import.meta.env.DEV) console.error('[Auth] logout error:', err);
    });
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
