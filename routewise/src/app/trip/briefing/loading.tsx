import { SiteHeader } from "~/components/SiteHeader";

export default function BriefingLoading() {
  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <SiteHeader active="routes" />
      <main className="mx-auto flex w-full max-w-[52rem] flex-col items-center justify-center gap-5 px-4 pt-32 sm:px-6">
        <div className="flex items-center gap-2.5 rounded-full bg-ink/90 px-5 py-2.5 shadow-[0_4px_20px_rgba(0,0,0,0.4)] backdrop-blur-md">
          <span className="flex items-center gap-[3px]">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="loading-dot inline-block h-1.5 w-1.5 rounded-full bg-paper/80"
                style={{ animationDelay: `${i * 0.15}s` }}
              />
            ))}
          </span>
          <span className="text-xs font-medium tracking-wide text-paper/90">
            Preparing your briefing…
          </span>
        </div>
      </main>
    </div>
  );
}
