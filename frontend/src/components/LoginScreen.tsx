import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Compass, Sparkles, ShieldCheck, ArrowRight, UserCheck, AlertCircle } from 'lucide-react';

export const LoginScreen: React.FC = () => {
  const { loginWithGoogle, devLogin, isFirebaseConfigured, loading } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isSigningIn, setIsSigningIn] = useState(false);
  const [devName, setDevName] = useState('');
  const [devEmail, setDevEmail] = useState('');
  const [showDevForm, setShowDevForm] = useState(false);

  const handleGoogleLogin = async () => {
    setError(null);
    setIsSigningIn(true);
    try {
      await loginWithGoogle();
    } catch (err: any) {
      console.error('Google Sign-In error:', err);
      setError(err?.message || 'Failed to sign in with Google. Please try again.');
    } finally {
      setIsSigningIn(false);
    }
  };

  const handleDevSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    devLogin(devName || 'Career Seeker', devEmail || 'seeker@careeradvisor.dev');
  };

  return (
    <div className="min-h-screen bg-[#0B0B0A] text-[#E8E6E3] flex flex-col justify-between selection:bg-[#D6A936]/30 selection:text-[#E8BA3E]">
      {/* Top ambient glow */}
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-full max-w-4xl h-72 bg-radial from-[#D6A936]/15 via-transparent to-transparent pointer-events-none blur-3xl -z-10" />

      {/* Header / Brand */}
      <header className="border-b border-[#242422]/60 px-6 py-4 flex items-center justify-between max-w-7xl mx-auto w-full">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#D6A936] to-[#997316] flex items-center justify-center text-[#0B0B0A] shadow-[0_0_20px_rgba(214,169,54,0.3)]">
            <Compass className="w-5 h-5 stroke-[2.5]" />
          </div>
          <div>
            <div className="text-base font-bold tracking-tight text-white flex items-center gap-2">
              Career Advisor <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-[#D6A936]/20 text-[#E8BA3E] border border-[#D6A936]/30">AI 2.0</span>
            </div>
            <p className="text-xs text-[#8E8C85]">Grounded Intelligence & Isolated Multi-User Workspaces</p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-[#8E8C85]">
          <ShieldCheck className="w-4 h-4 text-[#D6A936]" />
          <span>User-Isolated Data Protection</span>
        </div>
      </header>

      {/* Main Hero & Auth Card */}
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          {/* Card Container */}
          <div className="bg-[#141413] border border-[#262624] rounded-2xl p-8 shadow-2xl backdrop-blur-xl relative overflow-hidden">
            {/* Subtle card sheen */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-[#D6A936]/10 to-transparent pointer-events-none" />

            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-[#1B1B19] border border-[#2D2D2A] text-[#D6A936] mb-4 shadow-inner">
                <Sparkles className="w-7 h-7" />
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-white mb-2">
                Welcome to Career Advisor
              </h1>
              <p className="text-sm text-[#8E8C85] leading-relaxed">
                Sign in to access your private, AI-grounded career roadmap, isolated search history, and personalized resume reviews.
              </p>
            </div>

            {error && (
              <div className="mb-6 p-3.5 rounded-xl bg-red-950/40 border border-red-800/50 flex items-start gap-3 text-red-200 text-xs">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-400 mt-0.5" />
                <span className="leading-relaxed">{error}</span>
              </div>
            )}

            {/* Sign in Actions */}
            <div className="space-y-4">
              {/* Google Sign-in Button */}
              <button
                type="button"
                onClick={handleGoogleLogin}
                disabled={loading || isSigningIn}
                className="w-full h-12 rounded-xl bg-white hover:bg-gray-100 text-gray-900 font-medium text-sm flex items-center justify-center gap-3 transition-all duration-150 shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed group cursor-pointer"
              >
                <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
                <span>{isSigningIn ? 'Signing in with Google...' : 'Continue with Google'}</span>
                <ArrowRight className="w-4 h-4 ml-auto mr-1 text-gray-400 group-hover:translate-x-0.5 transition-transform" />
              </button>

              {/* Dev Mode / Quick Demo Sign In */}
              <div className="relative py-2">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-[#262624]" />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="bg-[#141413] px-3 text-[#6E6C65]">
                    {isFirebaseConfigured ? 'or quick test' : 'offline / local dev mode'}
                  </span>
                </div>
              </div>

              {!showDevForm ? (
                <button
                  type="button"
                  onClick={() => setShowDevForm(true)}
                  className="w-full h-10 rounded-xl bg-[#1B1B19] hover:bg-[#22221F] border border-[#2D2D2A] hover:border-[#3D3D39] text-[#C7C5BE] font-medium text-xs flex items-center justify-center gap-2 transition-all cursor-pointer"
                >
                  <UserCheck className="w-3.5 h-3.5 text-[#D6A936]" />
                  <span>Developer / Demo Workspace Sign-In</span>
                </button>
              ) : (
                <form onSubmit={handleDevSubmit} className="space-y-3 bg-[#181816] p-3.5 rounded-xl border border-[#2D2D2A]">
                  <div className="text-[11px] text-[#A8A69F] font-semibold">
                    Simulate an Authenticated User:
                  </div>
                  <div>
                    <input
                      type="text"
                      placeholder="Display Name (e.g. Alice Walker)"
                      value={devName}
                      onChange={(e) => setDevName(e.target.value)}
                      className="w-full px-3 py-2 text-xs bg-[#10100F] border border-[#2A2A28] rounded-lg text-white focus:outline-none focus:border-[#D6A936]"
                    />
                  </div>
                  <div>
                    <input
                      type="email"
                      placeholder="User Email (e.g. alice@example.com)"
                      value={devEmail}
                      onChange={(e) => setDevEmail(e.target.value)}
                      className="w-full px-3 py-2 text-xs bg-[#10100F] border border-[#2A2A28] rounded-lg text-white focus:outline-none focus:border-[#D6A936]"
                    />
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="submit"
                      className="flex-1 py-2 rounded-lg bg-[#D6A936] hover:bg-[#E8BA3E] text-[#0B0B0A] font-semibold text-xs transition-colors cursor-pointer"
                    >
                      Sign In to Workspace
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowDevForm(false)}
                      className="px-3 py-2 rounded-lg bg-[#222220] text-[#8E8C85] hover:text-white text-xs cursor-pointer"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              )}
            </div>

            {/* Privacy & Isolation Guarantee */}
            <div className="mt-8 pt-6 border-t border-[#20201E] text-center">
              <p className="text-[11px] text-[#787670] leading-normal">
                Your private workspace: chat conversations, queries, and resume uploads are encrypted and isolated strictly to your account.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-4 text-center text-xs text-[#5E5D57] border-t border-[#1C1C1A]">
        © {new Date().getFullYear()} Career Advisor AI • Powered by Groq LLM, LangChain & Cloud Firestore
      </footer>
    </div>
  );
};
