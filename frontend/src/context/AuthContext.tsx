import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import {
  signInWithPopup,
  signOut,
  onAuthStateChanged,
  type User as FirebaseUser,
} from 'firebase/auth';
import { auth, googleProvider, isFirebaseConfigured } from '@/lib/firebase';
import { setAuthToken } from '@/lib/api';

export interface UserProfile {
  uid: string;
  email: string | null;
  displayName: string | null;
  photoURL: string | null;
}

interface AuthContextType {
  user: UserProfile | null;
  idToken: string | null;
  loading: boolean;
  isFirebaseConfigured: boolean;
  loginWithGoogle: () => Promise<void>;
  devLogin: (name?: string, email?: string) => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const DEV_USER_STORAGE_KEY = 'career_advisor_dev_user';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [idToken, setIdToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Sync token to API client
  const updateSession = useCallback((token: string | null, profile: UserProfile | null) => {
    setIdToken(token);
    setUser(profile);
    setAuthToken(token);
  }, []);

  useEffect(() => {
    if (isFirebaseConfigured && auth) {
      const unsubscribe = onAuthStateChanged(auth, async (firebaseUser: FirebaseUser | null) => {
        if (firebaseUser) {
          try {
            const token = await firebaseUser.getIdToken();
            updateSession(token, {
              uid: firebaseUser.uid,
              email: firebaseUser.email,
              displayName: firebaseUser.displayName,
              photoURL: firebaseUser.photoURL,
            });
          } catch (err) {
            console.error('Failed to get Firebase ID token:', err);
            updateSession(null, null);
          }
        } else {
          updateSession(null, null);
        }
        setLoading(false);
      });
      return () => unsubscribe();
    } else {
      // Offline / Local Dev Auth Fallback
      const stored = localStorage.getItem(DEV_USER_STORAGE_KEY);
      if (stored) {
        try {
          const parsed = JSON.parse(stored) as UserProfile;
          const token = `dev-token:${parsed.uid}:${parsed.displayName || 'Dev'}:${parsed.email || ''}`;
          updateSession(token, parsed);
        } catch {
          localStorage.removeItem(DEV_USER_STORAGE_KEY);
        }
      }
      setLoading(false);
    }
  }, [updateSession]);

  const loginWithGoogle = async () => {
    if (!isFirebaseConfigured || !auth || !googleProvider) {
      throw new Error(
        'Firebase configuration is missing or incomplete. Please check your environment variables.'
      );
    }
    setLoading(true);
    try {
      const result = await signInWithPopup(auth, googleProvider);
      const token = await result.user.getIdToken();
      updateSession(token, {
        uid: result.user.uid,
        email: result.user.email,
        displayName: result.user.displayName,
        photoURL: result.user.photoURL,
      });
    } catch (err: any) {
      console.error('Firebase Google Sign-In error:', err);
      let userFriendlyMessage = 'Unable to sign in with Google. Please try again.';

      if (err?.code === 'auth/popup-closed-by-user') {
        userFriendlyMessage = 'Sign-in was cancelled before completion. Please try again.';
      } else if (err?.code === 'auth/popup-blocked') {
        userFriendlyMessage = 'The Google sign-in window was blocked by your browser. Please allow popups for this site.';
      } else if (err?.code === 'auth/unauthorized-domain') {
        const host = typeof window !== 'undefined' ? window.location.hostname : 'current domain';
        userFriendlyMessage = `Domain "${host}" is not authorized in Firebase. Please add "${host}" under Firebase Console > Authentication > Settings > Authorized domains.`;
      } else if (err?.code === 'auth/operation-not-allowed') {
        userFriendlyMessage = 'Google Sign-In is disabled in the Firebase Console. Please enable Google in Firebase Authentication > Sign-in method.';
      } else if (err?.code === 'auth/network-request-failed') {
        userFriendlyMessage = 'Network connection failed. Please check your internet connection and try again.';
      } else if (err?.code === 'auth/cancelled-popup-request') {
        userFriendlyMessage = 'Another sign-in request is in progress. Please try again.';
      } else if (err?.message) {
        userFriendlyMessage = err.message.replace(/^Firebase:\s*/, '').replace(/\s*\(auth\/[^)]+\)\.?$/, '');
      }

      const enhancedError = new Error(userFriendlyMessage);
      (enhancedError as any).code = err?.code;
      throw enhancedError;
    } finally {
      setLoading(false);
    }
  };

  const devLogin = (name = 'Career Seeker', email = 'seeker@careeradvisor.dev') => {
    const sanitizedName = name.trim() || 'Career Seeker';
    const sanitizedEmail = email.trim() || 'seeker@careeradvisor.dev';
    // Stable pseudo-ID from email/name or random
    const uid = 'dev-' + btoa(sanitizedEmail).replace(/[^a-zA-Z0-9]/g, '').slice(0, 16);
    const profile: UserProfile = {
      uid,
      email: sanitizedEmail,
      displayName: sanitizedName,
      photoURL: null,
    };
    const token = `dev-token:${uid}:${sanitizedName}:${sanitizedEmail}`;
    localStorage.setItem(DEV_USER_STORAGE_KEY, JSON.stringify(profile));
    updateSession(token, profile);
  };

  const logout = async () => {
    if (isFirebaseConfigured && auth) {
      await signOut(auth);
    }
    localStorage.removeItem(DEV_USER_STORAGE_KEY);
    updateSession(null, null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        idToken,
        loading,
        isFirebaseConfigured,
        loginWithGoogle,
        devLogin,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
