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
