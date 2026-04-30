import { AlertTriangle, Bot, Database, KeyRound, LockKeyhole, Radio, Send, ShieldCheck, UserRound } from "lucide-react";

const sections = [
  {
    title: "Owner Login",
    icon: UserRound,
    description: "Mandatory web login with Argon2id password hash and TOTP 2FA.",
    fields: [
      ["Owner email", "you@example.com", "email"],
      ["Owner password", "Minimum 12 characters", "password"],
      ["Confirm password", "Repeat password", "password"],
      ["TOTP code", "6 digits after QR enrollment", "text"]
    ]
  },
  {
    title: "Binance",
    icon: KeyRound,
    description: "Trade-only API credentials. Withdrawal must be disabled and IP restriction enabled.",
    fields: [
      ["BINANCE_API_KEY", "Binance API key", "password"],
      ["BINANCE_API_SECRET", "Binance API secret", "password"],
      ["BINANCE_TESTNET", "true or false", "text"],
      ["BINANCE_VIP_TIER", "0", "number"],
      ["Whitelisted VPS IP", "103.150.197.225", "text"]
    ]
  },
  {
    title: "OpenRouter AI",
    icon: Bot,
    description: "Analyst-only AI layer. It cannot execute orders or alter live risk settings.",
    fields: [
      ["OPENROUTER_API_KEY", "OpenRouter key", "password"],
      ["AI_PRIMARY_MODEL", "anthropic/claude-sonnet-4", "text"],
      ["AI_FAST_MODEL", "openai/gpt-4o-mini", "text"],
      ["AI_HEAVY_MODEL", "deepseek/deepseek-r1", "text"],
      ["AI_MAX_COST_USD_PER_DAY", "5.00", "number"]
    ]
  },
  {
    title: "Notifications",
    icon: Send,
    description: "Telegram for low-latency alerts, email for digest and critical fallback.",
    fields: [
      ["TELEGRAM_BOT_TOKEN", "Telegram bot token", "password"],
      ["TELEGRAM_CHAT_ID", "Telegram chat id", "text"],
      ["SMTP_HOST", "smtp.example.com", "text"],
      ["SMTP_USER", "SMTP username", "text"],
      ["SMTP_PASSWORD", "SMTP password", "password"],
      ["EMAIL_FROM", "alerts@yourdomain.com", "email"],
      ["EMAIL_TO", "you@yourdomain.com", "email"]
    ]
  },
  {
    title: "Monitoring & Recovery",
    icon: Radio,
    description: "External heartbeat and dead-man switch hooks for live safety.",
    fields: [
      ["HEALTHCHECK_PING_URL", "https://hc-ping.com/<uuid>", "url"],
      ["DEAD_MAN_SWITCH_WEBHOOK", "External flatten webhook", "url"],
      ["PROMETHEUS_ENABLED", "true", "text"]
    ]
  },
  {
    title: "Infrastructure",
    icon: Database,
    description: "Database, Redis, and JWT secrets. Change all defaults before production.",
    fields: [
      ["POSTGRES_PASSWORD", "Database password", "password"],
      ["DATABASE_URL", "postgresql+asyncpg://...", "password"],
      ["REDIS_PASSWORD", "Redis password", "password"],
      ["REDIS_URL", "redis://...", "password"],
      ["JWT_SECRET", "openssl rand -hex 64", "password"]
    ]
  }
];

function Field({ label, placeholder, type }: { label: string; placeholder: string; type: string }) {
  return (
    <label className="block">
      <span className="font-mono text-[10px] uppercase text-muted">{label}</span>
      <input
        type={type}
        placeholder={placeholder}
        className="mt-1 h-10 w-full rounded border border-white/10 bg-black/35 px-3 font-mono text-xs text-primary outline-none transition placeholder:text-muted focus:border-accent/60"
      />
    </label>
  );
}

export default function SettingsPage() {
  return (
    <div className="space-y-3">
      <section className="market-panel rounded px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="font-mono text-[11px] uppercase text-muted">Secure Configuration</div>
            <h1 className="mt-1 text-2xl font-semibold">Settings Vault</h1>
          </div>
          <div className="flex flex-wrap gap-2 font-mono text-[11px]">
            <span className="rounded border border-warning/30 bg-warning/10 px-2 py-1 text-warning">SAVE API PENDING BACKEND VAULT</span>
            <span className="rounded border border-profit/30 bg-profit/10 px-2 py-1 text-profit">NO BROWSER SECRET STORAGE</span>
          </div>
        </div>
      </section>

      <section className="market-panel rounded p-4">
        <div className="grid gap-3 lg:grid-cols-3">
          <div className="rounded border border-loss/30 bg-loss/10 p-3">
            <AlertTriangle className="mb-3 text-loss" size={18} />
            <div className="font-mono text-xs text-loss">Never enable Binance withdrawal permission.</div>
          </div>
          <div className="rounded border border-warning/30 bg-warning/10 p-3">
            <LockKeyhole className="mb-3 text-warning" size={18} />
            <div className="font-mono text-xs text-warning">Secrets must be encrypted server-side before real saving is enabled.</div>
          </div>
          <div className="rounded border border-profit/30 bg-profit/10 p-3">
            <ShieldCheck className="mb-3 text-profit" size={18} />
            <div className="font-mono text-xs text-profit">Risk hard limits remain immutable at runtime.</div>
          </div>
        </div>
      </section>

      <div className="grid gap-3 xl:grid-cols-2">
        {sections.map(({ title, icon: Icon, description, fields }) => (
          <section key={title} className="market-panel rounded">
            <div className="flex items-start gap-3 border-b border-white/10 p-4">
              <div className="grid h-10 w-10 place-items-center rounded border border-accent/30 bg-accent/10 text-accent">
                <Icon size={18} />
              </div>
              <div>
                <h2 className="font-mono text-sm uppercase text-primary">{title}</h2>
                <p className="mt-1 text-sm text-secondary">{description}</p>
              </div>
            </div>
            <div className="grid gap-3 p-4 sm:grid-cols-2">
              {fields.map(([label, placeholder, type]) => (
                <Field key={label} label={label} placeholder={placeholder} type={type} />
              ))}
            </div>
          </section>
        ))}
      </div>

      <section className="market-panel rounded p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-mono text-sm uppercase">Save Plan</h2>
            <p className="mt-1 text-sm text-secondary">
              This page is ready for input design. The next backend step is encrypted persistence with masked reads and audit logs.
            </p>
          </div>
          <div className="flex gap-2">
            <button className="h-10 rounded border border-white/10 px-4 font-mono text-xs text-secondary">TEST CONNECTIONS</button>
            <button className="h-10 rounded border border-accent/40 bg-accent/10 px-4 font-mono text-xs text-accent">SAVE ENCRYPTED</button>
          </div>
        </div>
      </section>
    </div>
  );
}
