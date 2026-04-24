/**
 * Coerce a user-supplied departure value into an ISO timestamp the backend
 * will accept, or `null` (which the backend treats as "depart now").
 *
 * Accepts:
 *   - `HH:MM` or `HH:MM:SS`            -> today at that local time, ISO
 *   - any string `Date` can parse       -> ISO of that
 *   - empty / undefined / unparseable    -> null
 */
export function parseDepart(input: string | null | undefined): string | null {
  if (!input) return null;
  const trimmed = input.trim();
  if (!trimmed) return null;

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
