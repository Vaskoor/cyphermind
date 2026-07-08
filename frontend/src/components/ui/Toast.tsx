'use client';

import { useEffect } from 'react';
import { AlertCircle, CheckCircle, Info, X, XCircle } from 'lucide-react';
import { useStore } from '@/store/useStore';
import type { Notification } from '@/lib/types';

const iconMap = {
  info: Info,
  success: CheckCircle,
  warning: AlertCircle,
  error: XCircle,
};

const styleMap = {
  info: 'border-info/30 bg-info/10 text-info',
  success: 'border-success/30 bg-success/10 text-success',
  warning: 'border-warning/30 bg-warning/10 text-warning',
  error: 'border-danger/30 bg-danger/10 text-danger',
};

function ToastItem({
  notification,
  onDismiss,
}: {
  notification: Notification;
  onDismiss: (id: string) => void;
}) {
  const Icon = iconMap[notification.type];

  useEffect(() => {
    const timer = setTimeout(() => onDismiss(notification.id), 5000);
    return () => clearTimeout(timer);
  }, [notification.id, onDismiss]);

  return (
    <div
      className={`pointer-events-auto flex w-80 items-start gap-3 rounded-lg border p-4 shadow-lg backdrop-blur-sm animate-in slide-in-from-right ${styleMap[notification.type]}`}
      style={{ backgroundColor: 'rgba(22, 27, 34, 0.95)' }}
    >
      <Icon className="mt-0.5 h-5 w-5 shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-white">{notification.title}</p>
        <p className="mt-0.5 text-xs text-muted">{notification.message}</p>
      </div>
      <button
        onClick={() => onDismiss(notification.id)}
        className="shrink-0 rounded p-0.5 text-muted transition-colors hover:text-white"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

export default function ToastContainer() {
  const { notifications, dismissNotification } = useStore();

  if (notifications.length === 0) return null;

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {notifications.slice(0, 5).map((n) => (
        <ToastItem key={n.id} notification={n} onDismiss={dismissNotification} />
      ))}
    </div>
  );
}

export function useToast() {
  const addNotification = useStore((s) => s.addNotification);

  return {
    toast: addNotification,
    success: (title: string, message: string) =>
      addNotification({ type: 'success', title, message }),
    error: (title: string, message: string) =>
      addNotification({ type: 'error', title, message }),
    info: (title: string, message: string) =>
      addNotification({ type: 'info', title, message }),
    warning: (title: string, message: string) =>
      addNotification({ type: 'warning', title, message }),
  };
}
