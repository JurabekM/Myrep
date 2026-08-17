import { create } from "zustand";

export interface UserProfile {
  industry?: string | null;
  business_type?: string | null;
  goals?: string[];
  location?: string | null;
  employees?: number | null;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "user" | "moderator" | "admin";
  plan: "free" | "pro" | "business" | "enterprise";
  locale: string;
  two_fa_enabled: boolean;
  profile: UserProfile;
}

interface AuthState {
  accessToken: string | null;
  user: User | null;
  setAccessToken: (token: string | null) => void;
  setUser: (user: User | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  setAccessToken: (accessToken) => set({ accessToken }),
  setUser: (user) => set({ user }),
  logout: () => {
    void fetch("/api/auth/logout", { method: "POST" });
    set({ accessToken: null, user: null });
    if (typeof window !== "undefined") window.location.href = "/login";
  },
}));
