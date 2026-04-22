import "server-only";

import { env } from "~/env";
import type {
  HotspotDetailResponse,
  TripBriefRequest,
  TripBriefResponse,
} from "~/lib/types";

class BackendError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "BackendError";
  }
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const url = `${env.BACKEND_URL}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new BackendError(res.status, `${res.status} ${url}: ${body.slice(0, 200)}`);
  }
  return (await res.json()) as T;
}

export async function fetchTripBrief(
  req: TripBriefRequest,
): Promise<TripBriefResponse> {
  const raw = await request<Partial<TripBriefResponse>>("/trip/brief", {
    method: "POST",
    body: JSON.stringify(req),
  });
  // Defensive defaults so a stale backend (missing the pivot fields)
  // never crashes the client. Every consumer of these arrays assumes they
  // exist; the Pydantic schema marks them as default-empty so the only way
  // they're missing is an out-of-date deployment.
  return {
    ...raw,
    alternates: raw.alternates ?? [],
    segments: raw.segments ?? [],
    hotspots: raw.hotspots ?? [],
    pre_trip_checklist: raw.pre_trip_checklist ?? [],
    chosen_route_id: raw.chosen_route_id ?? null,
    news_articles: raw.news_articles ?? [],
  } as TripBriefResponse;
}

export async function fetchHotspotDetail(
  id: string,
): Promise<HotspotDetailResponse> {
  return request<HotspotDetailResponse>(
    `/hotspots/${encodeURIComponent(id)}`,
    { method: "GET" },
  );
}

export { BackendError };

/**
 * Coerce a user-supplied departure value into an ISO timestamp the backend
 * will accept, or `null` (which the backend treats as "depart now").
 *
 * The landing form uses `<input type="time">`, which posts strings like
 * `"14:30"`. `new Date("14:30")` is "Invalid Date" in every JS runtime, so
 * calling `.toISOString()` on it throws `RangeError: Invalid time value` —
 * which is exactly the bug that surfaced as
 * "Could not reach the RouteWise backend: Invalid time value" on the trip
 * page (the error came from THIS process, not the backend at all).
 *
 * Accepts:
 *   - `HH:MM` or `HH:MM:SS`            -> today at that local time, ISO
 *   - any string `Date` can parse      -> ISO of that
 *   - empty / undefined / unparseable  -> null
 */
export function parseDepart(input: string | null | undefined): string | null {
  if (!input) return null;
  const trimmed = input.trim();
  if (!trimmed) return null;

  // Plain HH:MM[:SS] from <input type="time"> — anchor to today, local TZ.
  const timeOnly = /^(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(trimmed);
  if (timeOnly) {
    const [, hh, mm, ss] = timeOnly;
    const now = new Date();
    now.setHours(Number(hh), Number(mm), Number(ss ?? "0"), 0);
    return now.toISOString();
  }

  const d = new Date(trimmed);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}
