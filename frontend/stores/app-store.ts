import { create } from "zustand";

type AppState = {
  botStatus: "RUNNING" | "PAUSED" | "LOCKED";
  setBotStatus: (status: AppState["botStatus"]) => void;
};

export const useAppStore = create<AppState>((set) => ({
  botStatus: "PAUSED",
  setBotStatus: (botStatus) => set({ botStatus })
}));

