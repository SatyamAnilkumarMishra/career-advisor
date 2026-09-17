import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Compass, AlertCircle } from 'lucide-react';

export const LoginScreen: React.FC = () => {
  const { loginWithGoogle, loading } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isSigningIn, setIsSigningIn] = useState(false);

  const handleGoogleLogin = async () => {
    setError(null);
    setIsSigningIn(true);
    try {
      await loginWithGoogle();
    } catch (err: any) {
      setError(err?.message || 'Unable to sign in with Google. Please try again.');
    } finally {
      setIsSigningIn(false);
    }
  };

  const isBusy = loading || isSigningIn;

  return (
    <div className="auth-page-container">
      {/* Subtle ambient lighting */}
      <div className="auth-ambient-glow" aria-hidden="true" />

      {/* Centered Authentication Card */}
      <div className="auth-card">
        {/* Brand Icon */}
        <div className="auth-brand-logo">
          <Compass size={28} color="#080808" strokeWidth={2.2} />
        </div>

        {/* Clean, natural product headings */}
        <h1 className="auth-heading">Welcome back</h1>
        <p className="auth-subheading">
          Sign in to continue to your Career Advisor workspace.
        </p>

        {/* Actionable Error Banner */}
        {error && (
          <div className="auth-error-banner" role="alert">
            <AlertCircle className="auth-error-icon" />
            <span>{error}</span>
          </div>
        )}

        {/* Google Sign-in Button */}
        <button
          type="button"
          onClick={handleGoogleLogin}
          disabled={isBusy}
          className="auth-google-btn"
          aria-label="Continue with Google"
        >
          {isBusy ? (
            <>
              <span className="auth-spinner" aria-hidden="true" />
              <span>Signing in...</span>
            </>
          ) : (
            <>
              <svg className="auth-google-icon" viewBox="0 0 24 24" aria-hidden="true">
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
              <span>Continue with Google</span>
            </>
          )}
        </button>

        {/* Minimal Footer */}
        <div className="auth-card-footer">
          <p className="auth-footer-note">
            Secure authentication powered by Google
          </p>
        </div>
      </div>
    </div>
  );
};
