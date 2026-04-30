import { LockKeyhole, ShieldCheck } from "lucide-react";

export default function LoginPage() {
  return (
    <main className="terminal-grid grid min-h-screen place-items-center bg-base px-4">
      <form className="market-panel w-full max-w-md rounded p-6">
        <div className="flex items-center gap-3 border-b border-white/10 pb-5">
          <div className="grid h-11 w-11 place-items-center rounded border border-accent/30 bg-accent/10 text-accent">
            <LockKeyhole size={20} />
          </div>
          <div>
            <div className="font-mono text-[11px] uppercase text-muted">Secure owner access</div>
            <h1 className="text-xl font-semibold">AIQ-BOT Login</h1>
          </div>
        </div>

        <div className="mt-6 space-y-4">
          <label className="block">
            <span className="font-mono text-[10px] uppercase text-muted">Email</span>
            <input className="mt-1 h-11 w-full rounded border border-white/10 bg-black/35 px-3 text-sm outline-none focus:border-accent/60" placeholder="owner@example.com" type="email" />
          </label>
          <label className="block">
            <span className="font-mono text-[10px] uppercase text-muted">Password</span>
            <input className="mt-1 h-11 w-full rounded border border-white/10 bg-black/35 px-3 text-sm outline-none focus:border-accent/60" placeholder="Argon2id protected" type="password" />
          </label>
          <label className="block">
            <span className="font-mono text-[10px] uppercase text-muted">TOTP Code</span>
            <input className="mt-1 h-11 w-full rounded border border-white/10 bg-black/35 px-3 font-mono text-sm outline-none focus:border-accent/60" placeholder="000000" inputMode="numeric" />
          </label>
          <button className="flex h-11 w-full items-center justify-center gap-2 rounded border border-accent/40 bg-accent/15 font-mono text-sm text-accent">
            <ShieldCheck size={16} />
            AUTHENTICATE
          </button>
        </div>

        <div className="mt-5 rounded border border-warning/30 bg-warning/10 p-3 font-mono text-[11px] text-warning">
          Login API exists. Frontend submit wiring and encrypted session storage are the next implementation step.
        </div>
      </form>
    </main>
  );
}
