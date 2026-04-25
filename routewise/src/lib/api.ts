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
    alternates: (raw.alternates ?? []).map((a) => ({
      ...a,
      segments: a.segments ?? [],
    })),
    segments: raw.segments ?? [],
    hotspots: raw.hotspots ?? [],
    pre_trip_checklist: raw.pre_trip_checklist ?? [],
    chosen_route_id: raw.chosen_route_id ?? null,
    insights: raw.insights ?? [],
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

export { parseDepart } from "~/lib/parse-depart";
