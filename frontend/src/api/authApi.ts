import apiClient from '../lib/apiClient';
import type { LoginRequest, TokenResponse, UserRead } from '../types/api';

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<TokenResponse>('/api/v1/auth/login', data).then((r) => r.data),

  register: (data: RegisterRequest) =>
    apiClient.post<UserRead>('/api/v1/auth/register', data).then((r) => r.data),

  getCurrentUser: () =>
    apiClient.get<UserRead>('/api/v1/auth/me').then((r) => r.data),
};
