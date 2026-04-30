"use client";

import { useMemo, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://103.150.197.225:8000/api";

export type SettingsSection = {
  title: string;
  fields: [string, string, string][];
};

type SaveState = "idle" | "saving" | "saved" | "error";

export function SettingsForm({ sections }: { sections: SettingsSection[] }) {
  const [state, setState] = useState<SaveState>("idle");
  const [message, setMessage] = useState("Secrets are encrypted server-side and returned masked.");
  const fieldNames = useMemo(() => sections.flatMap((section) => section.fields.map(([label]) => label)), [sections]);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState("saving");
    const data = new FormData(event.currentTarget);
    const settings = fieldNames
      .map((key) => ({
        key,
        value: String(data.get(key) ?? ""),
        is_secret: true
      }))
      .filter((item) => item.value.trim() !== "");

    try {
      const response = await fetch(`${API_URL}/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ settings })
      });
      if (!response.ok) {
        throw new Error(`save failed: ${response.status}`);
      }
      setState("saved");
      setMessage(`Saved ${settings.length} configured setting(s). Refresh will show masked values once read wiring is expanded.`);
      event.currentTarget.reset();
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "failed to save settings");
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <div className="grid gap-3 xl:grid-cols-2">
        {sections.map(({ title, fields }) => (
          <section key={title} className="market-panel rounded">
            <div className="border-b border-white/10 p-4">
              <h2 className="font-mono text-sm uppercase text-primary">{title}</h2>
            </div>
            <div className="grid gap-3 p-4 sm:grid-cols-2">
              {fields.map(([label, placeholder, type]) => (
                <label key={label} className="block">
                  <span className="font-mono text-[10px] uppercase text-muted">{label}</span>
                  <input
                    name={label}
                    type={type}
                    placeholder={placeholder}
                    className="mt-1 h-10 w-full rounded border border-white/10 bg-black/35 px-3 font-mono text-xs text-primary outline-none transition placeholder:text-muted focus:border-accent/60"
                  />
                </label>
              ))}
            </div>
          </section>
        ))}
      </div>
      <section className="market-panel rounded p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-mono text-sm uppercase">Save Encrypted Settings</h2>
            <p className={`mt-1 text-sm ${state === "error" ? "text-loss" : state === "saved" ? "text-profit" : "text-secondary"}`}>
              {message}
            </p>
          </div>
          <div className="flex gap-2">
            <button type="button" className="h-10 rounded border border-white/10 px-4 font-mono text-xs text-secondary">
              TEST CONNECTIONS
            </button>
            <button type="submit" className="h-10 rounded border border-accent/40 bg-accent/10 px-4 font-mono text-xs text-accent">
              {state === "saving" ? "SAVING..." : "SAVE ENCRYPTED"}
            </button>
          </div>
        </div>
      </section>
    </form>
  );
}
