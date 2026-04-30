"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://103.150.197.225:8000/api";

export type SettingsSection = {
  title: string;
  fields: [string, string, string][];
};

type SaveState = "idle" | "saving" | "saved" | "error";

type SettingRead = {
  key: string;
  value: string | null;
  is_secret: boolean;
  configured: boolean;
};

type SettingsReadResponse = {
  settings: SettingRead[];
};

export function SettingsForm({ sections }: { sections: SettingsSection[] }) {
  const [state, setState] = useState<SaveState>("idle");
  const [message, setMessage] = useState("Loading encrypted settings status.");
  const [settingsByKey, setSettingsByKey] = useState<Record<string, SettingRead>>({});
  const [values, setValues] = useState<Record<string, string>>({});
  const fieldNames = useMemo(() => sections.flatMap((section) => section.fields.map(([label]) => label)), [sections]);

  async function fetchSettings() {
    const response = await fetch(`${API_URL}/settings`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`settings load failed: ${response.status}`);
    }
    return (await response.json()) as SettingsReadResponse;
  }

  const applySettings = useCallback((payload: SettingsReadResponse) => {
    const nextByKey = Object.fromEntries(payload.settings.map((item) => [item.key, item]));
    setSettingsByKey(nextByKey);
    setValues((current) => {
      const next = { ...current };
      for (const key of fieldNames) {
        const item = nextByKey[key];
        if (item?.configured && !item.is_secret && item.value !== null) {
          next[key] = item.value;
        } else if (next[key] === undefined) {
          next[key] = "";
        }
      }
      return next;
    });
    const configuredCount = payload.settings.filter((item) => item.configured).length;
    setMessage(`${configuredCount} setting(s) configured. Secret fields stay blank and only show masked placeholders.`);
  }, [fieldNames]);

  useEffect(() => {
    void fetchSettings().then(applySettings).catch((error: unknown) => {
      setState("error");
      setMessage(error instanceof Error ? error.message : "failed to load settings");
    });
  }, [applySettings]);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState("saving");
    const settings = fieldNames
      .map((key) => ({
        key,
        value: values[key] ?? "",
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
      const clearedSecrets = Object.fromEntries(
        fieldNames.map((key) => [key, settingsByKey[key]?.is_secret ? "" : (values[key] ?? "")])
      );
      setValues(clearedSecrets);
      applySettings(await fetchSettings());
      setState("saved");
      setMessage(`Saved ${settings.length} setting(s). Secret inputs were cleared after encrypted persistence.`);
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
              {fields.map(([label, placeholder, type]) => {
                const current = settingsByKey[label];
                const inputPlaceholder = current?.configured && current.value ? current.value : placeholder;
                return (
                  <label key={label} className="block">
                    <span className="flex items-center justify-between gap-2 font-mono text-[10px] uppercase text-muted">
                      <span>{label}</span>
                      <span className={current?.configured ? "text-profit" : "text-muted"}>
                        {current?.configured ? "CONFIGURED" : "EMPTY"}
                      </span>
                    </span>
                    <input
                      name={label}
                      type={type}
                      value={values[label] ?? ""}
                      onChange={(event) => setValues((currentValues) => ({ ...currentValues, [label]: event.target.value }))}
                      placeholder={inputPlaceholder}
                      className="mt-1 h-10 w-full rounded border border-white/10 bg-black/35 px-3 font-mono text-xs text-primary outline-none transition placeholder:text-muted focus:border-accent/60"
                    />
                  </label>
                );
              })}
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
