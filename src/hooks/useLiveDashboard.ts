import { useEffect, useRef, useState } from "react";
import type { DashboardState } from "../data/dashboardData";

const BACKEND_URL =
  (import.meta.env.VITE_BACKEND_URL as string | undefined) ??
  "http://localhost:8000";

const POLL_MS = 2000;

export type LiveDashboard = {
  state: DashboardState | null;
  isLoading: boolean;
  isLive: boolean;
  error: string | null;
  lastUpdated: Date | null;
};

export function useLiveDashboard(): LiveDashboard {
  const [state, setState] = useState<DashboardState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLive, setIsLive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const cancelled = useRef(false);

  useEffect(() => {
    cancelled.current = false;

    async function tick() {
      try {
        const resp = await fetch(`${BACKEND_URL}/state/dashboard`, {
          headers: { Accept: "application/json" },
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = (await resp.json()) as DashboardState;
        if (cancelled.current) return;
        setState(data);
        setIsLive(true);
        setError(null);
        setLastUpdated(new Date());
      } catch (err) {
        if (cancelled.current) return;
        setIsLive(false);
        setError(err instanceof Error ? err.message : "unknown error");
      } finally {
        if (!cancelled.current) setIsLoading(false);
      }
    }

    void tick();
    const handle = window.setInterval(tick, POLL_MS);
    return () => {
      cancelled.current = true;
      window.clearInterval(handle);
    };
  }, []);

  return { state, isLoading, isLive, error, lastUpdated };
}
