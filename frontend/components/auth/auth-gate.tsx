"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { clearAccessToken, getCurrentUser, getStoredAccessToken } from "@/lib/api";

type AuthState = "checking" | "authenticated" | "anonymous";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<AuthState>("checking");

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) {
      router.replace("/login");
      return;
    }

    void getCurrentUser(token)
      .then(() => setState("authenticated"))
      .catch(() => {
        clearAccessToken();
        setState("anonymous");
        router.replace("/login");
      });
  }, [router]);

  if (state === "checking") {
    return (
      <div className="grid min-h-screen place-items-center bg-base font-mono text-xs uppercase text-muted">
        Verifying session
      </div>
    );
  }

  if (state !== "authenticated") {
    return null;
  }

  return children;
}
