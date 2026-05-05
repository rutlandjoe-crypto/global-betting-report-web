type BettingSection = {
  key?: string;
  title?: string;
  headline?: string;
  snapshot?: string;
  signals?: string[];
  key_storylines?: string[];
  why_it_matters?: string[];
  what_to_watch?: string[];
  story_angles?: string[];
  advanced?: string[];
  updated_at?: string;
};

type ReportPayload = {
  title?: string;
  updated_at?: string;
  generated_at?: string;
  sections?: BettingSection[] | Record<string, BettingSection>;
};

async function getReport(): Promise<ReportPayload> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_SITE_URL || ""}/latest_report.json`, {
    cache: "no-store",
  });

  if (!res.ok) {
    return {};
  }

  return res.json();
}

function normalizeSections(sections: ReportPayload["sections"]): BettingSection[] {
  if (!sections) return [];
  if (Array.isArray(sections)) return sections;
  return Object.values(sections);
}

function getBettingSection(payload: ReportPayload): BettingSection | undefined {
  const sections = normalizeSections(payload.sections);

  return sections.find((section) => {
    const key = section.key?.toLowerCase() || "";
    const title = section.title?.toLowerCase() || "";
    return key.includes("betting") || title.includes("betting");
  });
}

function ListBlock({ title, items }: { title: string; items?: string[] }) {
  if (!items || items.length === 0) return null;

  return (
    <section className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-5 shadow-lg">
      <h2 className="mb-3 text-lg font-bold text-white">{title}</h2>
      <div className="space-y-2">
        {items.map((item, index) => (
          <div key={index} className="rounded-xl border border-zinc-800 bg-black/40 px-4 py-3 text-sm text-zinc-200">
            {item}
          </div>
        ))}
      </div>
    </section>
  );
}

export default async function BettingPage() {
  const payload = await getReport();
  const betting = getBettingSection(payload);

  const updatedAt = betting?.updated_at || payload.updated_at || payload.generated_at || "Updating";

  const signals =
    betting?.signals ||
    betting?.key_storylines ||
    betting?.advanced ||
    [];

  const whyItMatters = betting?.why_it_matters || [];
  const whatToWatch = betting?.what_to_watch || betting?.story_angles || [];

  return (
    <main className="min-h-screen bg-black px-4 py-8 text-white">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-3xl border border-zinc-800 bg-gradient-to-br from-zinc-950 to-black p-6 shadow-xl">
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-emerald-400">
            Global Betting Report
          </p>

          <h1 className="mt-3 text-3xl font-black tracking-tight md:text-5xl">
            Live betting intelligence layer
          </h1>

          <p className="mt-4 max-w-3xl text-base text-zinc-300 md:text-lg">
            Market signals, odds context, and sportsbook-facing story angles generated from the GSR Network editorial brain.
          </p>

          <div className="mt-5 rounded-2xl border border-emerald-900/60 bg-emerald-950/20 p-4 text-sm text-emerald-100">
            Updated: {updatedAt}
          </div>
        </header>

        <section className="rounded-3xl border border-zinc-800 bg-zinc-950 p-6 shadow-xl">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-zinc-400">
            Top Signal
          </p>

          <h2 className="mt-3 text-2xl font-black text-white">
            {betting?.headline || "Betting signals are being generated"}
          </h2>

          <p className="mt-3 text-zinc-300">
            {betting?.snapshot ||
              "The betting engine is checking market data and preparing the latest signal layer."}
          </p>
        </section>

        <div className="grid gap-6 md:grid-cols-3">
          <ListBlock title="Signals" items={signals} />
          <ListBlock title="Why It Matters" items={whyItMatters} />
          <ListBlock title="What To Watch" items={whatToWatch} />
        </div>

        <section className="rounded-3xl border border-zinc-800 bg-zinc-950/70 p-6">
          <h2 className="text-xl font-black">Editorial Standard</h2>
          <p className="mt-3 text-sm leading-6 text-zinc-300">
            This page organizes betting signals and market context. It is not betting advice. The purpose is to show how GSR Network can add structured data points and editorial context to the sports betting world.
          </p>
        </section>
      </div>
    </main>
  );
}