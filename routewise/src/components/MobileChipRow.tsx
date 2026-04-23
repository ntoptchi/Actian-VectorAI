"use client";

import Link from "next/link";
import type { HotspotSummary, NewsArticle } from "~/lib/types";

type Selection =
  | { kind: "hotspot"; data: HotspotSummary }
  | { kind: "news"; data: NewsArticle };

interface Props {
  hotspots: HotspotSummary[];
  newsArticles: NewsArticle[];
  briefingHref: string;
  onSelect: (s: Selection) => void;
}

export function MobileChipRow({
  hotspots,
  newsArticles,
  briefingHref,
  onSelect,
}: Props) {
  let chipIndex = 0;

  return (
    <div className="anim-chips-up absolute bottom-3 left-0 right-0 z-[1000] lg:hidden">
      <div
        className="flex gap-2 overflow-x-auto px-3 pb-[env(safe-area-inset-bottom)] scrollbar-none"
        style={{ WebkitOverflowScrolling: "touch" }}
      >
        {hotspots.map((h) => {
          const dot =
            (h.intensity_ratio ?? 0) >= 2.5
              ? "bg-alert"
              : (h.intensity_ratio ?? 0) >= 1.5
                ? "bg-gold"
                : "bg-good";
          const delay = chipIndex * 60;
          chipIndex++;
          return (
            <button
              key={h.hotspot_id}
              type="button"
              onClick={() => onSelect({ kind: "hotspot", data: h })}
              className="anim-chip-pop flex flex-none items-center gap-2 rounded-full bg-paper/95 px-3.5 py-2 text-xs font-medium text-ink shadow-md ring-1 ring-rule backdrop-blur-sm active:scale-95"
              style={{ animationDelay: `${delay}ms` }}
            >
              <span className={`h-2 w-2 shrink-0 rounded-full ${dot}`} />
              <span className="max-w-[120px] truncate">{h.label}</span>
            </button>
          );
        })}

        {newsArticles.map((n) => {
          const delay = chipIndex * 60;
          chipIndex++;
          return (
            <button
              key={n.article_id}
              type="button"
              onClick={() => onSelect({ kind: "news", data: n })}
              className="anim-chip-pop flex flex-none items-center gap-2 rounded-full bg-paper/95 px-3.5 py-2 text-xs font-medium text-ink shadow-md ring-1 ring-rule backdrop-blur-sm active:scale-95"
              style={{ animationDelay: `${delay}ms` }}
            >
              <span className="h-2 w-2 shrink-0 rounded-full bg-[#2563eb]" />
              <span className="max-w-[120px] truncate">{n.headline}</span>
            </button>
          );
        })}

        <Link
          href={briefingHref}
          className="anim-chip-pop flex flex-none items-center gap-2 rounded-full bg-ink/90 px-3.5 py-2 text-xs font-semibold text-paper shadow-md backdrop-blur-sm active:scale-95"
          style={{ animationDelay: `${chipIndex * 60}ms` }}
        >
          <svg
            width="12"
            height="12"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          >
            <rect x="3" y="2" width="10" height="12" rx="1.5" />
            <path d="M6 5h4M6 8h4M6 11h2" />
          </svg>
          Full briefing
        </Link>
      </div>
    </div>
  );
}
