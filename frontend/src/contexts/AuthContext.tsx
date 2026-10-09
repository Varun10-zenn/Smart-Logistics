import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import apiClient from '../lib/apiClient';
import { authApi, type RegisterRequest } from '../api/authApi';
import type { UserRead } from '../types/api';

interface AuthState {
  user: UserRead | null;
  token: string | null;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const IS_DEV_BYPASS = import.meta.env.VITE_DEV_AUTH_BYPASS === 'true';

const DEV_USER: UserRead = {
  id: 1,
  email: 'admin@smartlogistics.com',
  full_name: 'Development Operator',
  role: { id: 1, code: 'admin', description: 'Development Bypass Admin Role' },
  is_active: true,
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>(() => {
    if (IS_DEV_BYPASS) {
      return {
        user: DEV_USER,
        token: sessionStorage.getItem('access_token') || 'dev-bypass-token',
        isLoading: false,
      };
    }
    return {
      user: null,
      token: sessionStorage.getItem('access_token'),
      isLoading: true,
    };
  });

  // Hydrate user session on mount
  useEffect(() => {
    if (IS_DEV_BYPASS) {
      const storedToken = sessionStorage.getItem('access_token') || 'dev-bypass-token';
      setState({ user: DEV_USER, token: storedToken, isLoading: false });
      return;
    }

    const token = sessionStorage.getItem('access_token');
    const userStr = sessionStorage.getItem('user');
    if (token && userStr) {
      try {
        setState({ user: JSON.parse(userStr), token, isLoading: false });
      } catch {
        setState({ user: null, token: null, isLoading: false });
      }
    } else if (token) {
      // Fetch current user from /auth/me
      authApi
        .getCurrentUser()
        .then((userData) => {
          sessionStorage.setItem('user', JSON.stringify(userData));
          setState({ user: userData, token, isLoading: false });
        })
        .catch(() => {
          sessionStorage.removeItem('access_token');
          sessionStorage.removeItem('refresh_token');
          sessionStorage.removeItem('user');
          setState({ user: null, token: null, isLoading: false });
        });
    } else {
      setState({ user: null, token: null, isLoading: false });
    }
  }, []);

  // Listen for 401 events from the axios interceptor
  useEffect(() => {
    if (IS_DEV_BYPASS) return;
    const handler = () =>
      setState({ user: null, token: null, isLoading: false });
    window.addEventListener('auth:logout', handler);
    return () => window.removeEventListener('auth:logout', handler);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login({ email, password });
    const { access_token, refresh_token } = res;
    sessionStorage.setItem('access_token', access_token);
    if (refresh_token) {
      sessionStorage.setItem('refresh_token', refresh_token);
    }

    // Fetch current user details
    const meData = await authApi.getCurrentUser();
    sessionStorage.setItem('user', JSON.stringify(meData));
    setState({ user: meData, token: access_token, isLoading: false });
  }, []);

  const register = useCallback(async (data: RegisterRequest) => {
    await authApi.register(data);
    // After registration, automatically login
    await login(data.email, data.password);
  }, [login]);

  const logout = useCallback(async () => {
    try {
      await apiClient.post('/api/v1/auth/logout');
    } catch {
      // ignore logout API failures
    }
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('refresh_token');
    sessionStorage.removeItem('user');
    setState({ user: null, token: null, isLoading: false });
  }, []);

  return (
    <AuthContext.Provider
      value={{
        ...state,
        isAuthenticated: !!state.token && !!state.user,
        login,
        register,
        logout,
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
