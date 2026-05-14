import axios from "axios";

import { clearToken, getValidToken } from "./auth";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
const PUBLIC_BASE_URL = import.meta.env.VITE_PUBLIC_BASE_URL ?? "";

export const authApi = axios.create({
  baseURL: API_BASE_URL,
});

export const api = axios.create({
  baseURL: API_BASE_URL,
});

export const publicApi = axios.create({
  baseURL: PUBLIC_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = getValidToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearToken();
      if (window.location.pathname !== "/login") {
        window.location.assign("/login");
      }
    }
    return Promise.reject(error);
  },
);
