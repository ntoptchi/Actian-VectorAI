import { z } from "zod";

import { env } from "~/env";
import { createTRPCRouter, publicProcedure } from "~/server/api/trpc";
import type { TripBriefResponse } from "~/lib/types";

const latLon = z.object({
  lat: z.number(),
  lon: z.number(),
});

export const tripRouter = createTRPCRouter({
  brief: publicProcedure
    .input(
      z.object({
        origin: latLon,
        destination: latLon,
        timestamp: z.string().nullable().optional(),
      }),
    )
    .query(async ({ input }) => {
      const url = `${env.BACKEND_URL}/trip/brief`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(input),
        cache: "no-store",
      });
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(`backend ${res.status}: ${body.slice(0, 200)}`);
      }
      return (await res.json()) as TripBriefResponse;
    }),
});
