"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { api, setSessionExpiredHandler, tokens } from "@/core/api";
import type { TokenResponse, User } from "@/core/types";

type Auth = {
  /** null while unknown (server render / first paint), then the real state. */
  ready: boolean;
  signedIn: boolean;
  user: User | null;
  signIn: (data: TokenResponse) => void;
  signOut: () => Promise<void>;
  setUser: (user: User) => void;
  refreshUser: () => Promise<User | null>;
};

const Ctx = createContext<Auth | null>(null);

const subscribe = (fn: () => void) => tokens.subscribe(fn) as () => void;
const snapshot = () => (tokens.isSignedIn ? tokens.access ?? "" : "");

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  // The access token as the external store: signs in/out sync across tabs too.
  const access = useSyncExternalStore(subscribe, snapshot, () => null);
  const ready = access !== null;
  const signedIn = Boolean(access);
  const [user, setUserState] = useState<User | null>(null);

  useEffect(() => {
    if (signedIn) setUserState(tokens.user);
    else if (ready) setUserState(null);
  }, [signedIn, ready]);

  useEffect(() => {
    setSessionExpiredHandler(() => {
      const here = window.location.pathname + window.location.search;
      router.replace(`/login?next=${encodeURIComponent(here)}`);
    });
  }, [router]);

  const refreshUser = useCallback(async () => {
    if (!tokens.isSignedIn) return null;
    try {
      const me = await api.me();
      tokens.saveUser(me);
      setUserState(me);
      return me;
    } catch {
      return tokens.user;
    }
  }, []);

  useEffect(() => {
    if (signedIn) void refreshUser();
  }, [signedIn, refreshUser]);

  const value = useMemo<Auth>(
    () => ({
      ready,
      signedIn,
      user,
      signIn: (data) => {
        tokens.save(data);
        setUserState(data.user);
      },
      signOut: async () => {
        await api.logout();
        setUserState(null);
        router.replace("/");
      },
      setUser: (u) => {
        tokens.saveUser(u);
        setUserState(u);
      },
      refreshUser,
    }),
    [ready, signedIn, user, router, refreshUser]
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): Auth {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
