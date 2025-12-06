'use client';

import { createClient, getToken, signOut as supabaseSignOut } from '@/lib/auth/supabase';
import { User } from '@supabase/supabase-js';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

// Check if dev mode is enabled
const isDevMode = process.env.NEXT_PUBLIC_AUTH_PROVIDER === 'dev';

// Dev mode user
const DEV_USER = {
  id: '00000000-0000-0000-0000-000000000001',
  email: 'dev@dealguard.local',
  user_metadata: {
    full_name: 'Dev User',
    organization_id: '00000000-0000-0000-0000-000000000001',
  },
} as unknown as User;

// Dev mode token (backend accepts any token in dev mode)
const DEV_TOKEN = 'dev-token';

interface UseAuthReturn {
  user: User | null;
  loading: boolean;
  token: string | null;
  signOut: () => Promise<void>;
  refreshToken: () => Promise<string | null>;
}

export function useAuth(): UseAuthReturn {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Dev mode: use mock user immediately
    if (isDevMode) {
      setUser(DEV_USER);
      setToken(DEV_TOKEN);
      setLoading(false);
      return;
    }

    const supabase = createClient();

    // Get initial session
    const initAuth = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        setUser(session?.user ?? null);
        setToken(session?.access_token ?? null);
      } catch (error) {
        console.error('Auth init error:', error);
      } finally {
        setLoading(false);
      }
    };

    initAuth();

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        setUser(session?.user ?? null);
        setToken(session?.access_token ?? null);

        if (event === 'SIGNED_OUT') {
          router.push('/login');
        }
      }
    );

    return () => {
      subscription.unsubscribe();
    };
  }, [router]);

  const signOut = useCallback(async () => {
    if (isDevMode) {
      // In dev mode, just redirect to login (no real logout)
      router.push('/login');
      return;
    }
    await supabaseSignOut();
    setUser(null);
    setToken(null);
    router.push('/login');
  }, [router]);

  const refreshToken = useCallback(async () => {
    if (isDevMode) {
      return DEV_TOKEN;
    }
    const newToken = await getToken();
    setToken(newToken);
    return newToken;
  }, []);

  return {
    user,
    loading,
    token,
    signOut,
    refreshToken,
  };
}
