const ET_TIME_ZONE = "America/New_York";
const UNAVAILABLE = "Update time unavailable";
const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
] as const;

const etDisplayFormatter = new Intl.DateTimeFormat("en-US", {
  timeZone: ET_TIME_ZONE,
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
  hour12: true,
});

const legacyEtPattern =
  /^(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2})(?::\d{2}(?:\.\d+)?)?\s+(AM|PM)\s+ET$/i;

export function formatUpdatedAt(value: unknown): string {
  if (typeof value !== "string" || !value.trim()) return UNAVAILABLE;

  const raw = value.trim();
  const legacyMatch = raw.match(legacyEtPattern);
  if (legacyMatch) {
    const [, year, month, day, hour, minute, dayPeriod] = legacyMatch;
    const monthName = MONTHS[Number(month) - 1];
    if (monthName) {
      return `${monthName} ${Number(day)}, ${year} ${Number(hour)}:${minute} ${dayPeriod.toUpperCase()} ET`;
    }
  }

  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return UNAVAILABLE;

  const parts = Object.fromEntries(
    etDisplayFormatter
      .formatToParts(date)
      .filter(({ type }) => type !== "literal")
      .map(({ type, value: partValue }) => [type, partValue]),
  );

  return `${parts.month} ${parts.day}, ${parts.year} ${parts.hour}:${parts.minute} ${parts.dayPeriod} ET`;
}

