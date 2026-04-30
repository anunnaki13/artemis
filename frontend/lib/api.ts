const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export async function getDashboardSummary() {
  const response = await fetch(`${API_URL}/dashboard/summary`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("failed to load dashboard summary");
  }
  return response.json();
}

