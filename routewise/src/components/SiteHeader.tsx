import Link from "next/link";

interface Props {
  /** Navy ink-on-paper for the home page; transparent ivory rule for app pages. */
  variant?: "paper" | "flush";
  /** When set, that link gets the active treatment. */
  active?: "explore" | "routes" | "hotspots";
}

const NAV: Array<{ id: NonNullable<Props["active"]>; label: string; href: string }> = [
  { id: "explore", label: "Explore", href: "/" },
  { id: "routes", label: "Routes", href: "/trip" },
  { id: "hotspots", label: "Hotspots", href: "/#hotspots" },
];

export function SiteHeader({ variant = "paper", active }: Props) {
  const wrapper =
    variant === "paper"
      ? "border-b border-rule bg-paper/90 backdrop-blur"
      : "border-b border-rule/60 bg-paper-2/95 backdrop-blur";
  return (
    <header className={`sticky top-0 z-40 ${wrapper}`}>
      <div className="mx-auto flex h-14 max-w-[1400px] items-center gap-8 px-6">
        <Link
          href="/"
          className="group flex items-baseline gap-2"
          aria-label="RouteWise home"
        >
          <span className="font-display text-[1.35rem] font-medium tracking-tight text-ink">
            RouteWise
          </span>
          <span className="hidden h-1 w-1 rounded-full bg-gold transition group-hover:bg-alert sm:block" />
        </Link>

        <nav aria-label="Primary" className="hidden items-center gap-7 md:flex">
          {NAV.map((item) => {
            const isActive = active === item.id;
            return (
              <Link
                key={item.id}
                href={item.href}
                className={`text-sm transition ${
                  isActive
                    ? "font-semibold text-ink"
                    : "text-ink-3 hover:text-ink"
                }`}
              >
                {item.label}
                {isActive && (
                  <span className="mt-0.5 block h-[2px] w-full bg-ink" />
                )}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-4 text-ink-3">
          <button
            type="button"
            aria-label="Notifications"
            className="grid h-8 w-8 place-items-center rounded-full ring-1 ring-rule/70 transition hover:bg-paper-3 hover:text-ink"
          >
            <BellIcon />
          </button>
          <button
            type="button"
            aria-label="Account"
            className="grid h-8 w-8 place-items-center rounded-full ring-1 ring-rule/70 transition hover:bg-paper-3 hover:text-ink"
          >
            <UserIcon />
          </button>
        </div>
      </div>
    </header>
  );
}

function BellIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M3 12V8a5 5 0 1 1 10 0v4l1 1H2l1-1Z" />
      <path d="M6.5 14a1.5 1.5 0 0 0 3 0" />
    </svg>
  );
}

function UserIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="8" cy="6" r="2.5" />
      <path d="M3 14c0-2.5 2.2-4.2 5-4.2s5 1.7 5 4.2" />
    </svg>
  );
}
