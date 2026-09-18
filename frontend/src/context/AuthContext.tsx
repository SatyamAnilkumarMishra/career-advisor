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
  loginWithEmail: (email: string, password: string) => Promise<void>;
  registerWithEmail: (email: string, password: string, displayName?: string) => Promise<void>;
  devLogin: (name?: string, email?: string) => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const DEV_USER_STORAGE_KEY = 'career_advisor_dev_user';
const USERS_STORAGE_KEY = 'career_advisor_registered_users';
export const JUST_REGISTERED_STORAGE_KEY = 'career_advisor_just_registered_email';

function hashPassword(pwd: string): string {
  let h1 = 0xdeadbeef ^ 12345;
  let h2 = 0x41c6ce57 ^ 67890;
  for (let i = 0; i < pwd.length; i++) {
    const ch = pwd.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return (4294967296 * (2097151 & h2) + (h1 >>> 0)).toString(16);
}

interface LocalAccount {
  email: string;
  passwordHash: string;
  displayName: string;
  uid: string;
}

function getLocalUsers(): Record<string, LocalAccount> {
  try {
    const raw = localStorage.getItem(USERS_STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveLocalUser(account: LocalAccount): void {
  try {
    const users = getLocalUsers();
    users[account.email.toLowerCase()] = account;
    localStorage.setItem(USERS_STORAGE_KEY, JSON.stringify(users));
  } catch (err) {
    console.error('Failed to persist local user:', err);
  }
}

function formatAuthError(err: any): Error {
  console.error('Firebase Auth error:', err);
  let userFriendlyMessage = 'Authentication failed. Please try again.';

  if (err?.code === 'auth/popup-closed-by-user') {
    userFriendlyMessage = 'Sign-in window was closed before completion. Please try again.';
  } else if (err?.code === 'auth/popup-blocked') {
    userFriendlyMessage = 'The Google sign-in window was blocked by your browser. Please allow popups for this site.';
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
  } else if (err?.code === 'auth/user-not-found' || err?.code === 'auth/wrong-password' || err?.code === 'auth/invalid-credential') {
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
          // SECURITY: Firebase is configured, so it is the sole source of
          // truth for the session — there must be no fallback to a locally
          // stored dev-token here. Restoring one at this point is exactly
          // how a stale or fabricated local session used to grant access
          // even on a deployment with real Firebase auth. If any leftover
          // local dev session exists, discard it rather than honor it.
          localStorage.removeItem(DEV_USER_STORAGE_KEY);
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
    setLoading(true);

    if (!isFirebaseConfigured || !auth) {
      setLoading(false);
      throw new Error(
        'Google sign-in is not available because Firebase is not configured for this deployment. ' +
          'Set VITE_FIREBASE_API_KEY, VITE_FIREBASE_AUTH_DOMAIN, and VITE_FIREBASE_PROJECT_ID (see frontend/.env.example), then restart the app.'
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
      // SECURITY: any failure here — a real Firebase error, an unauthorized
      // domain, a misconfigured provider, anything — must surface to the
      // caller as a real error. There is no fallback account. Silently
      // logging someone in after a failed sign-in is the bug this replaces.
      console.warn('Firebase Google Sign-In attempt error:', err?.code, err?.message);
      throw formatAuthError(err);
    } finally {
      setLoading(false);
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

    setLoading(true);

    if (isFirebaseConfigured && auth) {
      // Firebase is configured: it is the sole source of truth. Any error
      // here — wrong password, unknown user, a real config problem — is
      // surfaced as-is. It must never fall through to the unverified local
      // account store, which would let a wrong password or a broken Firebase
      // setup "succeed" against a same-named local record instead of failing.
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
      } finally {
        setLoading(false);
      }
      return;
    }

    // Firebase is not configured for this deployment at all: fall back to
    // the local, browser-only account store. This path is only reachable
    // when isFirebaseConfigured is false, so it can never be used to bypass
    // a real, properly configured Firebase project.
    const localUsers = getLocalUsers();
    const existing = localUsers[cleanEmail];

    if (!existing) {
      setLoading(false);
      throw new Error('No account found with this email. Please switch to Register to create an account first.');
    }

    if (existing.passwordHash !== hashPassword(password)) {
      setLoading(false);
      throw new Error('Incorrect password. Please verify your credentials and try again.');
    }

    const profile: UserProfile = {
      uid: existing.uid,
      email: existing.email,
      displayName: existing.displayName,
      photoURL: null,
    };
    const token = `dev-token:${existing.uid}:${existing.displayName}:${existing.email}`;
    localStorage.setItem(DEV_USER_STORAGE_KEY, JSON.stringify(profile));
    updateSession(token, profile);
    setLoading(false);
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

    setLoading(true);

    if (isFirebaseConfigured && auth) {
      // Same rule as sign-in: once Firebase is configured, it is the only
      // path. A registration failure (email already in use, weak password,
      // a genuine config problem) must be reported, never quietly absorbed
      // into a separate local-only account.
      try {
        const result = await createUserWithEmailAndPassword(auth, cleanEmail, password);
        if (cleanName) {
          try {
            await updateProfile(result.user, { displayName: cleanName });
          } catch (profileErr) {
            console.warn('Failed to update display name:', profileErr);
          }
        }
        // Registration itself is already real (Firebase's own servers create
        // the account and enforce the password rules) but nothing so far
        // confirms this email address actually belongs to the person typing
        // it. sendEmailVerification triggers Firebase to send a real email
        // with a confirmation link to that inbox — this is the check that
        // was missing. Access to the app isn't gated on clicking it (that
        // would be a bigger UX change than asked for), so this is
        // best-effort: a failure here shouldn't block registration.
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
      } finally {
        setLoading(false);
      }
      return;
    }

    // Firebase is not configured for this deployment at all: register into
    // the local, browser-only account store instead.
    const localUsers = getLocalUsers();
    if (localUsers[cleanEmail]) {
      setLoading(false);
      throw new Error('An account with this email address already exists. Please sign in instead.');
    }

    const uid = 'usr_' + btoa(cleanEmail).replace(/[^a-zA-Z0-9]/g, '').slice(0, 16);
    const newAccount: LocalAccount = {
      email: cleanEmail,
      passwordHash: hashPassword(password),
      displayName: cleanName,
      uid,
    };
    saveLocalUser(newAccount);

    const profile: UserProfile = {
      uid,
      email: cleanEmail,
      displayName: cleanName,
      photoURL: null,
    };
    const token = `dev-token:${uid}:${cleanName}:${cleanEmail}`;
    localStorage.setItem(DEV_USER_STORAGE_KEY, JSON.stringify(profile));
    updateSession(token, profile);
    setLoading(false);
  };

  // Explicit, opt-in local developer session — never called automatically
  // by any login/register/error path above. Kept for local development
  // without a Firebase project. Refuses to run once Firebase IS configured,
  // so it can never be wired up (even by accident, e.g. a stray button) to
  // bypass a real deployment's authentication.
  const devLogin = (name = 'Career Seeker', email = 'seeker@careeradvisor.dev') => {
    if (isFirebaseConfigured) {
      console.error('devLogin() is disabled: Firebase is configured for this deployment.');
      return;
    }
    const sanitizedName = name.trim() || 'Career Seeker';
    const sanitizedEmail = email.trim() || 'seeker@careeradvisor.dev';
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
        loginWithEmail,
        registerWithEmail,
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