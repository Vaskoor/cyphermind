'use client';

import { usePathname } from 'next/navigation';
import Sidebar from './Sidebar';
import ToastContainer from '@/components/ui/Toast';

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLogin = pathname === '/login';

  if (isLogin) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <main className="ml-64 min-h-screen">
        <div className="p-6 lg:p-8">{children}</div>
      </main>
      <ToastContainer />
    </div>
  );
}
