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
  return request<TripBriefResponse>("/trip/brief", {
    method: "POST",
    body: JSON.stringify(req),
  });
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
