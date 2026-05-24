import { createFileRoute, redirect } from '@tanstack/react-router';
import { useState } from 'react';
import { useAuth } from '@/hooks/use-auth';
import { isAuthenticated } from '@/lib/auth/session';
import { ArrowRight, Mail, Lock, Loader2 } from 'lucide-react';
import logotype from '@/logotype.svg';
import { CodePreviewCard } from '@/components/login/code-preview-card';
import { DEFAULT_REDIRECTS } from '@/lib/constants/routes';
import { getCopyrightText } from '@/lib/constants/app';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export const Route = createFileRoute('/login')({
  component: LoginPage,
  beforeLoad: () => {
    if (typeof window !== 'undefined' && isAuthenticated()) {
      throw redirect({ to: DEFAULT_REDIRECTS.authenticated });
    }
  },
});

function LoginPage() {
  const { login, isLoggingIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    login({ email, password });
  };

  return (
    <div className="bg-background text-muted-foreground antialiased h-screen w-screen overflow-hidden selection:bg-primary/20 selection:text-foreground flex items-center justify-center p-4 sm:p-8 relative">
      {/* Global Background Elements */}
      <div className="absolute inset-0 bg-grid opacity-50" />

      {/* Centered Card Container */}
      <div className="w-full max-w-[1100px] h-full max-h-[700px] grid lg:grid-cols-2 bg-white border border-border rounded-xl overflow-hidden shadow-xl shadow-primary/5 relative z-10">
        {/* Left Section: Login Form */}
        <div className="flex flex-col justify-between p-8 sm:p-12 border-b lg:border-b-0 lg:border-r border-border bg-white">
          {/* Header/Logo */}
          <img src={logotype} alt="Sandtuari Connect" className="h-30" />

          {/* Main Form Container */}
          <div className="w-full max-w-sm mx-auto space-y-6 my-auto py-8">
            <div className="space-y-2">
              <h1 className="text-2xl font-medium tracking-tight text-foreground">
                Welcome back
              </h1>
              <p className="text-sm text-muted-foreground">
                Sign in to access dashboard, users, and settings.
              </p>
            </div>

            <form className="space-y-4" onSubmit={handleLogin}>
              {/* Email Input */}
              <div className="space-y-1.5">
                <Label htmlFor="email" className="text-xs text-foreground-muted">
                  Email address
                </Label>
                <div className="relative group">
                  <Input
                    type="email"
                    id="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="bg-white border-border pr-10"
                    placeholder="developer@example.com"
                    required
                  />
                  <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none opacity-0 group-focus-within:opacity-100 transition-opacity">
                    <Mail className="w-4 h-4 text-muted-foreground" />
                  </div>
                </div>
              </div>

              {/* Password Input */}
              <div className="space-y-1.5">
                <Label htmlFor="password" className="text-xs text-foreground-muted">
                  Password
                </Label>
                <div className="relative group">
                  <Input
                    type="password"
                    id="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="bg-white border-border pr-10"
                    placeholder="••••••••"
                    required
                  />
                  <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none opacity-0 group-focus-within:opacity-100 transition-opacity">
                    <Lock className="w-4 h-4 text-muted-foreground" />
                  </div>
                </div>
              </div>

              {/* Submit Button */}
              <Button type="submit" disabled={isLoggingIn} className="w-full">
                {isLoggingIn ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  <>
                    Sign in
                    <ArrowRight className="w-4 h-4 opacity-60" />
                  </>
                )}
              </Button>
            </form>
          </div>

          {/* Footer Links */}
          <div className="flex items-center text-xs text-muted-foreground">
            <p>{getCopyrightText()}</p>
          </div>
        </div>

        {/* Right Section: Visuals/Context */}
        <div className="hidden lg:flex flex-col relative bg-muted/50 overflow-hidden">
          <CodePreviewCard />
        </div>
      </div>
    </div>
  );
}
