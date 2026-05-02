"use client";

import { useEffect, useState } from "react";

import {
  type AiAnalystBriefResponse,
  type AiAnalystBudgetResponse,
  type AiAnalystRunResponse,
  generateAiAnalystBrief,
  getAiAnalystBudget,
  getAiAnalystQueue,
  getAiAnalystRuns,
  reviewAiAnalystRun,
} from "@/lib/api";

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="market-panel rounded">
      <div className="flex h-10 items-center border-b border-white/10 px-3">
        <h2 className="font-mono text-[11px] uppercase text-secondary">{title}</h2>
      </div>
      <div className="p-3">{children}</div>
    </section>
  );
}

function formatNumber(value: string | number | null | undefined, digits = 2) {
  if (value === null || value === undefined) return "--";
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "--";
  return parsed.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export default function AiAnalystPage() {
  const [mode, setMode] = useState<"fast" | "primary" | "heavy">("primary");
  const [question, setQuestion] = useState("");
  const [budget, setBudget] = useState<AiAnalystBudgetResponse | null>(null);
  const [runs, setRuns] = useState<AiAnalystRunResponse[]>([]);
  const [queue, setQueue] = useState<AiAnalystRunResponse[]>([]);
  const [brief, setBrief] = useState<AiAnalystBriefResponse | null>(null);
  const [selectedRun, setSelectedRun] = useState<AiAnalystRunResponse | null>(null);
  const [reviewNotes, setReviewNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadMeta = async () => {
    const [budgetResult, runsResult, queueResult] = await Promise.allSettled([
      getAiAnalystBudget(),
      getAiAnalystRuns(12),
      getAiAnalystQueue(8),
    ]);
    if (budgetResult.status === "fulfilled") setBudget(budgetResult.value);
    if (runsResult.status === "fulfilled") {
      setRuns(runsResult.value);
      setSelectedRun((current) => current ? runsResult.value.find((item) => item.id === current.id) ?? current : runsResult.value[0] ?? null);
    }
    if (queueResult.status === "fulfilled") setQueue(queueResult.value);
  };

  useEffect(() => {
    void loadMeta();
  }, []);

  const submit = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await generateAiAnalystBrief({ mode, question });
      setBrief(response);
      setSelectedRun(response.run);
      setReviewNotes(response.run.review_notes ?? "");
      await loadMeta();
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI brief generation failed");
    } finally {
      setLoading(false);
    }
  };

  const review = async (reviewStatus: "approved" | "rejected" | "follow_up") => {
    if (!selectedRun) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await reviewAiAnalystRun(selectedRun.id, {
        review_status: reviewStatus,
        review_notes: reviewNotes,
      });
      setSelectedRun(updated);
      if (brief?.run.id === updated.id) {
        setBrief({ ...brief, run: updated });
      }
      await loadMeta();
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI review update failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="market-panel rounded px-4 py-3">
        <div className="font-mono text-[11px] uppercase text-muted">AI Analyst</div>
        <h1 className="mt-1 text-2xl font-semibold">Read-Only OpenRouter Analyst</h1>
        <p className="mt-1 text-sm text-secondary">
          This page now calls OpenRouter against live backend context. It is budget-guarded, read-only, and cannot submit execution actions.
        </p>
      </div>

      <div className="grid gap-3 xl:grid-cols-[0.95fr_1.05fr]">
        <Panel title="Analyst Control">
          <div className="space-y-3">
            <div className="grid gap-2 sm:grid-cols-3 font-mono text-xs">
              {(["fast", "primary", "heavy"] as const).map((candidate) => (
                <button
                  key={candidate}
                  type="button"
                  onClick={() => setMode(candidate)}
                  className={`rounded border px-3 py-2 ${
                    mode === candidate
                      ? "border-cyan/40 bg-cyan/10 text-cyan"
                      : "border-white/10 bg-black/20 text-secondary"
                  }`}
                >
                  {candidate.toUpperCase()}
                </button>
              ))}
            </div>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Optional operator question. Example: Why are replacement alerts elevated today?"
              className="h-32 w-full rounded border border-white/10 bg-black/20 px-3 py-2 text-sm text-primary outline-none"
            />
            <button
              type="button"
              onClick={() => void submit()}
              disabled={loading}
              className="h-11 w-full rounded border border-profit/30 bg-profit/10 font-mono text-xs text-profit disabled:opacity-60"
            >
              {loading ? "GENERATING..." : "GENERATE AI BRIEF"}
            </button>
            {error ? <div className="text-sm text-loss">{error}</div> : null}
          </div>
        </Panel>

        <Panel title="Budget">
          <div className="grid gap-3 sm:grid-cols-3">
            <Metric label="Limit / day" value={`$${formatNumber(budget?.limit_usd, 2)}`} />
            <Metric label="Spent today" value={`$${formatNumber(budget?.spent_today_usd, 4)}`} />
            <Metric label="Remaining" value={`$${formatNumber(budget?.remaining_usd, 4)}`} />
          </div>
          <div className="mt-3 rounded border border-white/10 bg-black/20 px-3 py-2 text-xs text-secondary">
            Analyst mode is read-only. It can inspect dashboard, lineage, venue, and hold-quality state, but it cannot change risk, settings, or execution lifecycle.
          </div>
        </Panel>
      </div>

      <div className="grid gap-3 xl:grid-cols-[1.05fr_0.95fr]">
        <Panel title="Latest AI Brief">
          {selectedRun ? (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-3 font-mono text-xs text-secondary">
                <span>model {selectedRun.model}</span>
                <span>status {selectedRun.status}</span>
                <span>review {selectedRun.review_status}</span>
                <span>cost ${formatNumber(selectedRun.estimated_cost_usd, 6)}</span>
                <span>{selectedRun.input_tokens ?? 0} in / {selectedRun.output_tokens ?? 0} out</span>
              </div>
              <div className="whitespace-pre-wrap rounded border border-white/10 bg-black/20 px-3 py-3 text-sm text-primary">
                {selectedRun.response_text ?? "No response text returned."}
              </div>
              <textarea
                value={reviewNotes}
                onChange={(event) => setReviewNotes(event.target.value)}
                placeholder="Review notes for operator follow-up."
                className="h-24 w-full rounded border border-white/10 bg-black/20 px-3 py-2 text-sm text-primary outline-none"
              />
              <div className="grid gap-2 sm:grid-cols-3 font-mono text-xs">
                <button type="button" disabled={loading} onClick={() => void review("approved")} className="h-10 rounded border border-profit/30 bg-profit/10 text-profit disabled:opacity-60">APPROVE</button>
                <button type="button" disabled={loading} onClick={() => void review("follow_up")} className="h-10 rounded border border-warning/30 bg-warning/10 text-warning disabled:opacity-60">FOLLOW UP</button>
                <button type="button" disabled={loading} onClick={() => void review("rejected")} className="h-10 rounded border border-loss/30 bg-loss/10 text-loss disabled:opacity-60">REJECT</button>
              </div>
            </div>
          ) : (
            <div className="text-sm text-muted">No AI brief generated yet.</div>
          )}
        </Panel>

        <Panel title="AI Review Queue">
          <div className="space-y-2 font-mono text-xs">
            {queue.length === 0 ? (
              <div className="text-muted">No pending AI reviews.</div>
            ) : (
              queue.map((run) => (
                <div key={run.id} className="rounded border border-white/10 bg-black/20 px-3 py-2">
                  <button type="button" onClick={() => {
                    setSelectedRun(run);
                    setReviewNotes(run.review_notes ?? "");
                  }} className="w-full text-left">
                  <div className="flex items-center justify-between">
                    <span className="text-primary">{run.mode.toUpperCase()} / {run.model}</span>
                    <span className="text-warning">{run.review_status}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-secondary">
                    <span>{run.status}</span>
                    <span>${formatNumber(run.estimated_cost_usd, 6)}</span>
                    <span>{run.input_tokens ?? 0} in / {run.output_tokens ?? 0} out</span>
                  </div>
                  </button>
                </div>
              ))
            )}
          </div>
        </Panel>
      </div>

      <Panel title="Recent AI Runs">
        <div className="space-y-2 font-mono text-xs">
          {runs.length === 0 ? (
            <div className="text-muted">No AI runs yet.</div>
          ) : (
            runs.map((run) => (
              <button
                key={run.id}
                type="button"
                onClick={() => {
                  setSelectedRun(run);
                  setReviewNotes(run.review_notes ?? "");
                }}
                className={`w-full rounded border px-3 py-2 text-left ${
                  selectedRun?.id === run.id ? "border-cyan/40 bg-cyan/10" : "border-white/10 bg-black/20"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-primary">{run.mode.toUpperCase()} / {run.model}</span>
                  <span className={run.review_status === "approved" ? "text-profit" : run.review_status === "rejected" ? "text-loss" : "text-warning"}>
                    {run.review_status}
                  </span>
                </div>
                <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-secondary">
                  <span>{run.status}</span>
                  <span>${formatNumber(run.estimated_cost_usd, 6)}</span>
                  <span>{run.input_tokens ?? 0} in / {run.output_tokens ?? 0} out</span>
                </div>
              </button>
            ))
          )}
        </div>
      </Panel>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-white/10 bg-black/25 px-3 py-2 font-mono text-xs">
      <div className="text-muted">{label}</div>
      <div className="mt-1 text-primary">{value}</div>
    </div>
  );
}
