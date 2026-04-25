import { env } from "~/env";
import type {
  RoutesOnlyResponse,
  TripBriefRequest,
  TripBriefResponse,
} from "~/lib/types";

const BASE = env.NEXT_PUBLIC_BACKEND_URL;

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${path}: ${text.slice(0, 200)}`);
  }
  return (await res.json()) as T;
}

export function fetchRoutes(req: TripBriefRequest): Promise<RoutesOnlyResponse> {
  return post<RoutesOnlyResponse>("/trip/routes", req);
}

export function fetchBrief(req: TripBriefRequest): Promise<TripBriefResponse> {
  return post<Partial<TripBriefResponse>>("/trip/brief", req).then((raw) => ({
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
  })) as Promise<TripBriefResponse>;
}
