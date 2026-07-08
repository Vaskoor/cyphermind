'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Bot,
  Brain,
  FileText,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Network,
  PlusCircle,
  Settings,
  Shield,
  Swords,
  Bug,
} from 'lucide-react';
import { useStore } from '@/store/useStore';

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/engagements/new', label: 'New Engagement', icon: PlusCircle },
  { href: '/bug-bounty', label: 'Bug Bounty', icon: Bug },
  { href: '/chat', label: 'AI Chat', icon: MessageSquare },
  { href: '/knowledge', label: 'Knowledge', icon: Brain },
  { href: '/selfplay', label: 'Self-Play', icon: Swords },
  { href: '/reports', label: 'Reports', icon: FileText },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useStore();

  const isActive = (href: string) => {
    if (href === '/dashboard') return pathname === '/dashboard';
    return pathname.startsWith(href);
  };

  if (pathname === '/login') return null;

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-64 flex-col border-r border-border bg-surface">
      <div className="flex items-center gap-3 border-b border-border px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/20 shadow-glow-sm">
          <Shield className="h-5 w-5 text-accent" />
        </div>
        <div>
          <h1 className="text-sm font-bold tracking-wide text-white">CypherMind</h1>
          <p className="text-xs text-muted">AI Security Platform</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              className={`group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                active
                  ? 'bg-accent/15 text-accent shadow-glow-sm'
                  : 'text-muted hover:bg-surface-hover hover:text-white'
              }`}
            >
              <Icon
                className={`h-4 w-4 transition-colors ${
                  active ? 'text-accent' : 'text-muted group-hover:text-white'
                }`}
              />
              {label}
              {active && (
                <span className="ml-auto h-1.5 w-1.5 rounded-full bg-accent animate-pulse-slow" />
              )}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border p-4">
        {user ? (
          <div className="space-y-3">
            <div className="flex items-center gap-3 rounded-lg bg-background/50 px-3 py-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/20">
                <Bot className="h-4 w-4 text-accent" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-white">{user.username}</p>
                <p className="truncate text-xs text-muted">{user.email}</p>
              </div>
            </div>
            <button
              onClick={logout}
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted transition-colors hover:bg-danger/10 hover:text-danger"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </div>
        ) : (
          <Link
            href="/login"
            className="flex items-center gap-2 rounded-lg bg-accent px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hover"
          >
            <Network className="h-4 w-4" />
            Sign in
          </Link>
        )}
      </div>
    </aside>
  );
}
