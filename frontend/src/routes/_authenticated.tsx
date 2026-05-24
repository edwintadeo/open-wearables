import { createFileRoute, Outlet, redirect } from '@tanstack/react-router';
import { SimpleSidebar } from '@/components/layout/simple-sidebar';
import { isAuthenticated } from '@/lib/auth/session';
import { DEFAULT_REDIRECTS } from '@/lib/constants/routes';

export const Route = createFileRoute('/_authenticated')({
  component: AuthenticatedLayout,
  beforeLoad: () => {
    // Skip auth check during SSR - localStorage is not available on the server
    // The check will run on the client after hydration
    if (typeof window === 'undefined') {
      return;
    }
    if (!isAuthenticated()) {
      throw redirect({ to: DEFAULT_REDIRECTS.unauthenticated });
    }
  },
});

function AuthenticatedLayout() {
  return (
    <div className="flex min-h-screen w-full bg-background">
      <SimpleSidebar />
      <main className="flex-1 overflow-auto bg-background border-l border-border/50">
        <Outlet />
      </main>
    </div>
  );
}
