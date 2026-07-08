import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Finding, Notification, User } from '@/lib/types';

interface AppState {
  user: User | null;
  token: string | null;
  findings: Finding[];
  notifications: Notification[];

  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  logout: () => void;

  setFindings: (findings: Finding[]) => void;
  addFinding: (finding: Finding) => void;
  updateFinding: (id: string, updates: Partial<Finding>) => void;

  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  markNotificationRead: (id: string) => void;
  clearNotifications: () => void;
  dismissNotification: (id: string) => void;
}

let notificationCounter = 0;

export const useStore = create<AppState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      findings: [],
      notifications: [],

      setUser: (user) => set({ user }),

      setToken: (token) => {
        if (typeof window !== 'undefined') {
          if (token) {
            localStorage.setItem('cyphermind_token', token);
          } else {
            localStorage.removeItem('cyphermind_token');
          }
        }
        set({ token });
      },

      logout: () => {
        if (typeof window !== 'undefined') {
          localStorage.removeItem('cyphermind_token');
        }
        set({ user: null, token: null, findings: [], notifications: [] });
      },

      setFindings: (findings) => set({ findings }),

      addFinding: (finding) =>
        set((state) => ({
          findings: [finding, ...state.findings.filter((f) => f.id !== finding.id)],
        })),

      updateFinding: (id, updates) =>
        set((state) => ({
          findings: state.findings.map((f) => (f.id === id ? { ...f, ...updates } : f)),
        })),

      addNotification: (notification) =>
        set((state) => ({
          notifications: [
            {
              ...notification,
              id: `notif-${++notificationCounter}-${Date.now()}`,
              timestamp: new Date().toISOString(),
              read: false,
            },
            ...state.notifications,
          ].slice(0, 50),
        })),

      markNotificationRead: (id) =>
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, read: true } : n
          ),
        })),

      clearNotifications: () => set({ notifications: [] }),

      dismissNotification: (id) =>
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        })),
    }),
    {
      name: 'cyphermind-store',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
      }),
    }
  )
);
