import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import {
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  updateProfile,
  sendEmailVerification,
  signOut,
  onAuthStateChanged,
  GoogleAuthProvider,
  type User as FirebaseUser,
} from 'firebase/auth';
import { auth, isFirebaseConfigured } from '@/lib/firebase';
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
  loginWithEmail: (email: string, password: string) => Promise<void>;
  registerWithEmail: (email: string, password: string, displayName?: string) => Promise<void>;
  devLogin: (name?: string, email?: string) => void;
  logout: () => Promise<void>;
}
const AuthContext = createContext<AuthContextType | undefined>(undefined);
export const JUST_REGISTERED_STORAGE_KEY = 'career_advisor_just_registered_email';
function formatAuthError(err: any): Error {
  console.error('Firebase Auth error:', err);
  let userFriendlyMessage = 'Authentication failed. Please try again.';
  if (err?.code === 'auth/popup-closed-by-user') {
    userFriendlyMessage = 'Sign-in window was closed before completion. Please try again.';
  } else if (err?.code === 'auth/popup-blocked') {
    userFriendlyMessage = 'The Google sign-in popup was blocked by your browser. Please allow popups for this site.';
  } else if (err?.code === 'auth/unauthorized-domain') {
    const host = typeof window !== 'undefined' ? window.location.hostname : 'current domain';
    userFriendlyMessage = `Domain "${host}" is not authorized in Firebase. Please add "${host}" under Firebase Console > Authentication > Settings > Authorized domains.`;
  } else if (err?.code === 'auth/operation-not-allowed') {
    userFriendlyMessage = 'This sign-in method is disabled in the Firebase Console. Please enable Email/Password or Google under Authentication > Sign-in method.';
  } else if (err?.code === 'auth/email-already-in-use') {
    userFriendlyMessage = 'An account with this email address already exists. Please sign in instead.';
  } else if (err?.code === 'auth/invalid-email') {
    userFriendlyMessage = 'Please enter a valid email address.';
  } else if (err?.code === 'auth/weak-password') {
    userFriendlyMessage = 'Password must be at least 6 characters long.';
  } else if (
    err?.code === 'auth/user-not-found' ||
    err?.code === 'auth/wrong-password' ||
    err?.code === 'auth/invalid-credential' ||
    err?.message?.includes('INVALID_LOGIN_CREDENTIALS')
  ) {
    userFriendlyMessage = 'Invalid email or password. Please verify your credentials and try again.';
  } else if (err?.code === 'auth/account-exists-with-different-credential') {
    userFriendlyMessage = 'An account already exists with this email using a different sign-in provider (e.g. Google).';
  } else if (err?.code === 'auth/too-many-requests') {
    userFriendlyMessage = 'Access to this account has been temporarily disabled due to many failed login attempts. Please wait a moment and try again.';
  } else if (err?.code === 'auth/network-request-failed') {
    userFriendlyMessage = 'Network connection error. Please check your internet connection and try again.';
  } else if (err?.code === 'auth/cancelled-popup-request') {
    userFriendlyMessage = 'Another sign-in request is already in progress. Please try again.';
  } else if (err?.message) {
    userFriendlyMessage = err.message.replace(/^Firebase:\s*/, '').replace(/\s*\(auth\/[^)]+\)\.?$/, '');
  }
  const enhancedError = new Error(userFriendlyMessage);
  (enhancedError as any).code = err?.code;
  return enhancedError;
}
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
    // Purge any stale dev tokens from previous test sessions
    try {
      localStorage.removeItem('career_advisor_dev_user');
    } catch {
      // ignore
    }

        if (isFirebaseConfigured && auth) {
      // onIdTokenChanged listens to sign-in, sign-out, and automatic hourly token refreshes
      const unsubscribe = onIdTokenChanged(auth, async (firebaseUser: FirebaseUser | null) => {
        if (firebaseUser) {
          try {
            const token = await firebaseUser.getIdToken();
            updateSession(token, {
              uid: firebaseUser.uid,
              email: firebaseUser.email,
              displayName: firebaseUser.displayName || (firebaseUser.email ? firebaseUser.email.split('@')[0] : 'User'),
              photoURL: firebaseUser.photoURL,
            });
          } catch (err) {
            console.error('Failed to obtain fresh Firebase ID token:', err);
            updateSession(null, null);
          }
        } else {
          updateSession(null, null);
        }
        setLoading(false);
      });
      return () => unsubscribe();
    } else {
      setLoading(false);
    }
  }, [updateSession]);
  const loginWithGoogle = async () => {
    if (!isFirebaseConfigured || !auth) {
      throw new Error(
        'Google sign-in is not available because Firebase is not configured for this deployment. ' +
          'Set VITE_FIREBASE_API_KEY, VITE_FIREBASE_AUTH_DOMAIN, and VITE_FIREBASE_PROJECT_ID in your environment.'
      );
    }
    try {
      const provider = new GoogleAuthProvider();
      provider.setCustomParameters({
        prompt: 'select_account',
      });
      provider.addScope('email');
      provider.addScope('profile');
      const result = await signInWithPopup(auth, provider);
      const token = await result.user.getIdToken();
      updateSession(token, {
        uid: result.user.uid,
        email: result.user.email,
        displayName: result.user.displayName,
        photoURL: result.user.photoURL,
      });
    } catch (err: any) {
      console.warn('Firebase Google Sign-In attempt error:', err?.code, err?.message);
      throw formatAuthError(err);
    }
  };
  const loginWithEmail = async (email: string, password: string) => {
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !cleanEmail.includes('@') || !cleanEmail.includes('.')) {
      throw new Error('Please enter a valid email address.');
    }
    if (!password) {
      throw new Error('Please enter your password.');
    }
    if (!isFirebaseConfigured || !auth) {
      throw new Error('Authentication service is not configured.');
    }
    try {
      const result = await signInWithEmailAndPassword(auth, cleanEmail, password);
      const token = await result.user.getIdToken();
      updateSession(token, {
        uid: result.user.uid,
        email: result.user.email,
        displayName: result.user.displayName || cleanEmail.split('@')[0],
        photoURL: result.user.photoURL,
      });
    } catch (err: any) {
      console.warn('Firebase login attempt:', err?.code, err?.message);
      throw formatAuthError(err);
    }
  };
  const registerWithEmail = async (email: string, password: string, displayName?: string) => {
    const cleanEmail = email.trim().toLowerCase();
    const cleanName = displayName?.trim() || cleanEmail.split('@')[0];
    if (!cleanEmail || !cleanEmail.includes('@') || !cleanEmail.includes('.')) {
      throw new Error('Please enter a valid email address.');
    }
    if (!password || password.length < 6) {
      throw new Error('Password must be at least 6 characters long.');
    }
    if (!isFirebaseConfigured || !auth) {
      throw new Error('Authentication service is not configured.');
    }
    try {
      const result = await createUserWithEmailAndPassword(auth, cleanEmail, password);
      if (cleanName) {
        try {
          await updateProfile(result.user, { displayName: cleanName });
        } catch (profileErr) {
          console.warn('Failed to update display name:', profileErr);
        }
      }
      try {
        await sendEmailVerification(result.user);
        sessionStorage.setItem(JUST_REGISTERED_STORAGE_KEY, cleanEmail);
      } catch (verifyErr) {
        console.warn('Failed to send verification email:', verifyErr);
      }
      const token = await result.user.getIdToken();
      updateSession(token, {
        uid: result.user.uid,
        email: result.user.email,
        displayName: cleanName || result.user.displayName,
        photoURL: result.user.photoURL,
      });
    } catch (err: any) {
      console.warn('Firebase registration attempt:', err?.code, err?.message);
      throw formatAuthError(err);
    }
  };
  const devLogin = () => {
    console.warn('devLogin is disabled in production.');
  };
  const logout = async () => {
    if (isFirebaseConfigured && auth) {
      await signOut(auth);
    }
    updateSession(null, null);
  };
