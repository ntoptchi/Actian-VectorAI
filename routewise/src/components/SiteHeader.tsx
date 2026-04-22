import Link from "next/link";

interface Props {
  /** Navy ink-on-paper for the home page; transparent ivory rule for app pages. */
  variant?: "paper" | "flush";
  /** When set, that link gets the active treatment. */
  active?: "explore" | "routes";
}

const NAV: Array<{ id: NonNullable<Props["active"]>; label: string; href: string }> = [
  { id: "explore", label: "Explore", href: "/" },
  { id: "routes", label: "Routes", href: "/trip" },
];

export function SiteHeader({ variant = "paper", active }: Props) {
  const wrapper =
    variant === "paper"
      ? "border-b border-rule bg-paper/85 backdrop-blur"
      : "border-b border-rule/60 bg-paper-2/95 backdrop-blur";
  return (
    <header className={`sticky top-0 z-40 ${wrapper}`}>
      <div className="mx-auto flex h-14 max-w-[1400px] items-center gap-8 px-6">
        <Link
          href="/"
          className="flex items-center gap-2"
          aria-label="RouteWise home"
        >
          <span
            aria-hidden
            className="grid h-6 w-6 place-items-center rounded-md bg-ink text-paper-3"
          >
            <LogoMark />
          </span>
          <span className="text-base font-semibold tracking-tight text-ink">
            RouteWise
          </span>
        </Link>

        <nav aria-label="Primary" className="hidden items-center gap-6 md:flex">
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
              </Link>
            );
          })}
        </nav>

        <span className="ml-auto hidden text-xs text-ink-4 sm:inline">
          Free · no signup
        </span>
      </div>
    </header>
  );
}

function LogoMark() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M2 9.5 L5 6 L7 8 L10 3" />
      <circle cx="10" cy="3" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}
