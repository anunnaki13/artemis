"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, Copy, KeyRound, LockKeyhole, QrCode, ShieldCheck, UserPlus } from "lucide-react";

import { loginOwner, registerOwner, type RegisterResponse } from "@/lib/api";

type Mode = "login" | "register";
type SubmitState = "idle" | "loading" | "success" | "error";

export function LoginForm() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [state, setState] = useState<SubmitState>("idle");
  const [message, setMessage] = useState("Owner access requires password plus a valid TOTP code.");
  const [setup, setSetup] = useState<RegisterResponse | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState("loading");
    const data = new FormData(event.currentTarget);
    const email = String(data.get("email") ?? "");
    const password = String(data.get("password") ?? "");
    const totpCode = String(data.get("totp_code") ?? "");

    try {
      if (mode === "register") {
        const registered = await registerOwner({ email, password });
        setSetup(registered);
        setMode("login");
        setState("success");
        setMessage("Owner created. Add the TOTP secret to your authenticator, then login with the 6-digit code.");
        return;
      }

      await loginOwner({ email, password, totp_code: totpCode });
      setState("success");
      setMessage("Authenticated. Redirecting to dashboard.");
      router.push("/dashboard");
      router.refresh();
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "authentication failed");
    }
  }

  async function copySetupValue(value: string) {
    await navigator.clipboard.writeText(value);
    setMessage("TOTP setup value copied.");
  }

  const isLoading = state === "loading";

  return (
    <form onSubmit={onSubmit} className="market-panel w-full max-w-5xl rounded">
      <div className="grid lg:grid-cols-[0.92fr_1.08fr]">
        <section className="border-b border-white/10 p-5 lg:border-b-0 lg:border-r">
          <div className="flex items-center gap-3 border-b border-white/10 pb-5">
            <div className="grid h-11 w-11 place-items-center rounded border border-accent/30 bg-accent/10 text-accent">
              <LockKeyhole size={20} />
            </div>
            <div>
              <div className="font-mono text-[11px] uppercase text-muted">Secure owner access</div>
              <h1 className="text-xl font-semibold">AIQ-BOT Login</h1>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-2 rounded border border-white/10 bg-black/30 p-1 font-mono text-xs">
            <button
              type="button"
              onClick={() => setMode("login")}
              className={`h-10 rounded ${mode === "login" ? "bg-accent/15 text-accent" : "text-secondary"}`}
            >
              LOGIN
            </button>
            <button
              type="button"
              onClick={() => setMode("register")}
              className={`h-10 rounded ${mode === "register" ? "bg-accent/15 text-accent" : "text-secondary"}`}
            >
              REGISTER
            </button>
          </div>

          <div className="mt-5 space-y-4">
            <label className="block">
              <span className="font-mono text-[10px] uppercase text-muted">Email</span>
              <input
                name="email"
                className="mt-1 h-11 w-full rounded border border-white/10 bg-black/35 px-3 text-sm outline-none focus:border-accent/60"
                placeholder="owner@example.com"
                type="email"
                autoComplete="email"
                required
              />
            </label>
            <label className="block">
              <span className="font-mono text-[10px] uppercase text-muted">Password</span>
              <input
                name="password"
                className="mt-1 h-11 w-full rounded border border-white/10 bg-black/35 px-3 text-sm outline-none focus:border-accent/60"
                placeholder={mode === "register" ? "Minimum 12 characters" : "Argon2id protected"}
                type="password"
                autoComplete={mode === "register" ? "new-password" : "current-password"}
                minLength={mode === "register" ? 12 : undefined}
                required
              />
            </label>
            {mode === "login" ? (
              <label className="block">
                <span className="font-mono text-[10px] uppercase text-muted">TOTP Code</span>
                <input
                  name="totp_code"
                  className="mt-1 h-11 w-full rounded border border-white/10 bg-black/35 px-3 font-mono text-sm outline-none focus:border-accent/60"
                  placeholder="000000"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  minLength={6}
                  maxLength={8}
                  required
                />
              </label>
            ) : null}
            <button
              disabled={isLoading}
              className="flex h-11 w-full items-center justify-center gap-2 rounded border border-accent/40 bg-accent/15 font-mono text-sm text-accent disabled:cursor-wait disabled:opacity-60"
            >
              {mode === "register" ? <UserPlus size={16} /> : <ShieldCheck size={16} />}
              {isLoading ? "PROCESSING..." : mode === "register" ? "CREATE OWNER" : "AUTHENTICATE"}
            </button>
          </div>

          <div
            className={`mt-5 rounded border p-3 font-mono text-[11px] ${
              state === "error"
                ? "border-loss/30 bg-loss/10 text-loss"
                : state === "success"
                  ? "border-profit/30 bg-profit/10 text-profit"
                  : "border-warning/30 bg-warning/10 text-warning"
            }`}
          >
            {message}
          </div>
        </section>

        <section className="p-5">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded border border-profit/30 bg-profit/10 text-profit">
              <QrCode size={18} />
            </div>
            <div>
              <h2 className="font-mono text-sm uppercase text-primary">TOTP Enrollment</h2>
              <p className="mt-1 text-sm text-secondary">Register once, then add the generated secret to your authenticator app.</p>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            <div className="rounded border border-white/10 bg-black/30 p-4">
              <div className="mb-2 flex items-center gap-2 font-mono text-[11px] uppercase text-muted">
                <KeyRound size={14} />
                TOTP Secret
              </div>
              <div className="break-all font-mono text-sm text-primary">{setup?.totp_secret ?? "Register an owner account to generate this value."}</div>
              {setup ? (
                <button
                  type="button"
                  onClick={() => copySetupValue(setup.totp_secret)}
                  className="mt-3 inline-flex h-9 items-center gap-2 rounded border border-white/10 px-3 font-mono text-xs text-secondary hover:text-primary"
                >
                  <Copy size={14} />
                  COPY SECRET
                </button>
              ) : null}
            </div>

            <div className="rounded border border-white/10 bg-black/30 p-4">
              <div className="mb-2 flex items-center gap-2 font-mono text-[11px] uppercase text-muted">
                <CheckCircle2 size={14} />
                Provisioning URI
              </div>
              <div className="break-all font-mono text-xs text-secondary">{setup?.provisioning_uri ?? "Waiting for owner registration."}</div>
              {setup ? (
                <button
                  type="button"
                  onClick={() => copySetupValue(setup.provisioning_uri)}
                  className="mt-3 inline-flex h-9 items-center gap-2 rounded border border-white/10 px-3 font-mono text-xs text-secondary hover:text-primary"
                >
                  <Copy size={14} />
                  COPY URI
                </button>
              ) : null}
            </div>

            <div className="rounded border border-warning/30 bg-warning/10 p-4 font-mono text-[11px] text-warning">
              Save the TOTP secret immediately. The backend returns it only during registration.
            </div>
          </div>
        </section>
      </div>
    </form>
  );
}
