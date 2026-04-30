"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { getCurrentUser } from "@/lib/api";

type AuthState = "checking" | "authenticated" | "anonymous";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<AuthState>("checking");

  useEffect(() => {
    void getCurrentUser()
      .then(() => setState("authenticated"))
      .catch(() => {
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
