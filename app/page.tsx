import fs from "fs";
import path from "path";
import type { Metadata } from "next";

export const dynamic = "force-dynamic";
export const revalidate = 0;
export const fetchCache = "force-no-store";

import EditorialStandard from "@/components/EditorialStandard";

export const metadata: Metadata = {
  title: "Global Betting Report",
  description:
    "Global Betting Report tracks odds, implied probability, line movement, weather angles, and betting market context.",
};

type AnyObj = Record<string, any>;

const SITE = {
  name: "Global Betting Report",
  tagline: "Built for journalists, by a journalist.",
  topic: "Betting",
  descriptor:
    "Global Betting Report tracks odds, implied probability, line movement, weather angles, betting market context, and newsroom-ready intelligence across MLB, NBA, NFL, NHL, soccer, tennis, golf, combat sports, college football and the broader sports calendar.",
};

const TOOLKIT = [
  ["OddsTrader", "https://www.oddstrader.com/"],
  ["OddsTrader MLB Weather", "https://www.oddstrader.com/mlb/weather/"],
  ["The Odds API", "https://the-odds-api.com/"],
  ["Action Network", "https://www.actionnetwork.com/"],
  ["Covers", "https://www.covers.com/"],
  ["Sportsbook Review", "https://www.sportsbookreview.com/"],
];

const GSR_NETWORK = [
  ["Sports", "https://globalsportsreport.com"],
  ["AI", "https://globalaireport.news"],
  ["Politics", "https://globalpoliticsreport.com"],
  ["Entertainment", "https://globalentertainmentreport.com"],
  ["Betting", "https://globalbettingreport.com"],
];

const DEFAULT_URL = "https://www.oddstrader.com/";
const WEATHER_URL = "https://www.oddstrader.com/mlb/weather/";

const BAD_CONTENT_PHRASES = [
  "source refresh",
  "refresh needed",
  "needed before publication",
  "strict mode",
  "current-day update pending",
  "feed checked",
  "required date",
  "rebuild distribution",
  "bad or stale",
  "not allowed onto the homepage",
  "no verified data point attached yet",
  "no current items available",
  "undefined sports category",
  "undefined",
];

const SPORT_LABELS: Record<string, string> = {
  mlb: "MLB",
  baseball: "MLB",
  nba: "NBA",
  basketball: "NBA",
  nfl: "NFL",
  football: "NFL",
  ncaafb: "College Football",
  cfb: "College Football",
  "college football": "College Football",
  nhl: "NHL",
  hockey: "NHL",
  soccer: "Global Soccer",
  tennis: "Tennis",
  golf: "Golf",
  mma: "MMA",
  ufc: "UFC",
  boxing: "Boxing",
  racing: "Racing",
  nascar: "NASCAR",
  cricket: "Cricket",
  rugby: "Rugby",
  betting: "Betting Watch",
};

function readReport(): AnyObj {
  try {
    const file = path.join(process.cwd(), "public", "latest_report.json");
    const raw = fs.readFileSync(file, "utf8");
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

function cleanText(value: any): string {
  if (value === null || value === undefined) return "";

  if (Array.isArray(value)) {
    return value.map(cleanText).filter(Boolean).join(" • ");
  }

  if (typeof value === "object") {
    return Object.values(value).map(cleanText).filter(Boolean).join(" • ");
  }

  return String(value).replace(/\s+/g, " ").trim();
}

function normalizeText(value: any): string {
  return cleanText(value).toLowerCase();
}

function isBadContent(value: any): boolean {
  const text = normalizeText(value);
  if (!text) return true;
  return BAD_CONTENT_PHRASES.some((phrase) => text.includes(phrase));
}

function unique(items: string[]): string[] {
  const seen = new Set<string>();

  return items
    .map((item) => item.replace(/\s+/g, " ").trim())
    .filter((item) => {
      if (!item) return false;
      const key = item.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

function asList(value: any): string[] {
  if (!value) return [];

  if (Array.isArray(value)) {
    return value.flatMap((item) =>
      cleanText(item)
        .split(/\n|•/)
        .map((x) => x.trim())
        .filter(Boolean)
    );
  }

  if (typeof value === "object") {
    return Object.values(value).flatMap((item) =>
      cleanText(item)
        .split(/\n|•/)
        .map((x) => x.trim())
        .filter(Boolean)
    );
  }

  return cleanText(value)
    .split(/\n|•/)
    .map((x) => x.trim())
    .filter(Boolean);
}

function isValidUrl(value: any): boolean {
  const url = cleanText(value);
  return url.startsWith("http://") || url.startsWith("https://");
}

function extractBestUrl(story: AnyObj): string {
  const directCandidates = [
    story.url,
    story.link,
    story.source_url,
    story.sourceUrl,
    story.href,
    story.web_url,
    story.webUrl,
  ];

  for (const candidate of directCandidates) {
    if (isValidUrl(candidate)) return cleanText(candidate);
  }

  const label = normalizeText(story.league || story.sport || story.category || story.title);
  if (label.includes("weather") || label.includes("mlb")) return WEATHER_URL;

  return DEFAULT_URL;
}

function normalizeSportLabel(value: any, fallback = "Betting Watch"): string {
  const raw = cleanText(value);
  const key = raw.toLowerCase();

  if (!raw || key === "undefined" || key === "null" || key === "sports category") {
    return fallback;
  }

  return SPORT_LABELS[key] || raw;
}

function storyTitle(story: AnyObj, index: number): string {
  return (
    cleanText(story.headline) ||
    cleanText(story.title) ||
    cleanText(story.name) ||
    normalizeSportLabel(story.league || story.sport || story.category, "") ||
    `Betting Storyline ${index + 1}`
  );
}

function storyUrl(story: AnyObj): string {
  return extractBestUrl(story);
}

function storySummary(story: AnyObj): string {
  return (
    cleanText(story.snapshot) ||
    cleanText(story.summary) ||
    cleanText(story.description) ||
    cleanText(story.why_it_matters) ||
    cleanText(story.body) ||
    "Betting development flagged for newsroom monitoring with odds, price, movement and context attached where available."
  );
}

function storyLabel(story: AnyObj): string {
  return normalizeSportLabel(
    story.league || story.sport || story.category || story.label || story.title,
    "Betting Watch"
  );
}

function enrichKeyData(story: AnyObj, title: string): string[] {
  const direct = asList(story.key_data || story.keyData || story.data || story.metrics);

  const odds = cleanText(story.odds || story.price || story.moneyline || story.spread || story.total);
  const implied = cleanText(story.implied_probability || story.impliedProbability);
  const movement = cleanText(story.line_movement || story.lineMovement || story.movement);
  const weather = cleanText(story.weather || story.forecast || story.weather_angle || story.weatherAngle);

  return unique([
    ...direct,
    odds ? `Odds/price: ${odds}` : "",
    implied ? `Implied probability: ${implied}` : "",
    movement ? `Line movement: ${movement}` : "",
    weather ? `Weather angle: ${weather}` : "",
    !direct.length && !odds && !implied && !movement ? `Signal: ${title}` : "",
  ]).filter((item) => !isBadContent(item));
}

function enrichWhy(story: AnyObj): string[] {
  const direct = asList(story.why_it_matters || story.whyItMatters || story.why);

  return unique([
    ...direct,
    "Betting readers need more than the number — they need context on whether price, public money, injuries, matchup edges or weather may be driving the market.",
  ]).filter((item) => !isBadContent(item));
}

function enrichWatch(story: AnyObj): string[] {
  const direct = asList(story.what_to_watch || story.whatToWatch || story.watch || story.story_angles);

  return unique([
    ...direct,
    "Watch for injury updates, lineup confirmations, pitching changes, weather shifts, totals movement, spread movement and late sportsbook adjustment.",
  ]).filter((item) => !isBadContent(item));
}

function normalizeStory(story: AnyObj, index: number, sectionTitle = ""): AnyObj {
  const title = storyTitle(story, index);
  const rawLabel = story.league || story.sport || story.category || sectionTitle || story.title;
  const label = normalizeSportLabel(rawLabel, "Betting Watch");

  return {
    ...story,
    id: cleanText(story.id || story.key || `${label}-${index}`),
    key: cleanText(story.key || story.id || `${label}-${index}`),
    league: label,
    title,
    headline: title,
    summary: storySummary(story),
    snapshot: storySummary(story),
    url: storyUrl(story),
    key_data: enrichKeyData(story, title),
    why_it_matters: enrichWhy(story),
    what_to_watch: enrichWatch(story),
  };
}

function sectionToStories(section: AnyObj, index: number): AnyObj[] {
  const sectionTitle = normalizeSportLabel(section.title || section.league || section.sport || `Section ${index + 1}`);

  if (Array.isArray(section.cards) && section.cards.length) {
    const objectCards = section.cards.filter((card: any) => card && typeof card === "object");
    const stringCards = section.cards.filter((card: any) => typeof card === "string");

    if (objectCards.length) {
      return objectCards.map((card: AnyObj, cardIndex: number) =>
        normalizeStory(card, cardIndex, sectionTitle)
      );
    }

    if (stringCards.length) {
      return [
        normalizeStory(
          {
            league: sectionTitle,
            title: sectionTitle,
            headline: sectionTitle,
            snapshot:
              "Latest verified betting signals generated for newsroom review with market context attached.",
            key_data: stringCards,
            why_it_matters: [
              "This section gives readers betting market context beyond a raw odds board.",
            ],
            what_to_watch: [
              "Watch for line movement, injury updates, weather changes, book-to-book differences and late market shifts.",
            ],
            url: DEFAULT_URL,
          },
          index,
          sectionTitle
        ),
      ];
    }
  }

  return [
    normalizeStory(
      {
        league: sectionTitle,
        title: sectionTitle,
        headline: cleanText(section.headline || section.title || sectionTitle),
        snapshot: cleanText(section.snapshot || section.summary || section.description),
        key_data: asList(section.key_data || section.keyData || section.cards),
        why_it_matters: asList(section.why_it_matters || section.whyItMatters || section.why),
        what_to_watch: asList(section.what_to_watch || section.whatToWatch || section.watch),
        url: extractBestUrl(section),
      },
      index,
      sectionTitle
    ),
  ];
}

function getStories(report: AnyObj): AnyObj[] {
  if (Array.isArray(report.sections) && report.sections.length) {
    return report.sections.flatMap((section: AnyObj, index: number) =>
      sectionToStories(section || {}, index)
    );
  }

  const candidates =
    report.live_newsroom ||
    report.homepage_cards ||
    report.cards ||
    report.stories ||
    report.news ||
    report.headlines ||
    report.items ||
    report.articles ||
    [];

  if (Array.isArray(candidates)) {
    return candidates
      .filter((story) => story && typeof story === "object")
      .map((story, index) => normalizeStory(story, index));
  }

  return [];
}

function getSpotlightStories(report: AnyObj, key: "live_newsroom" | "editor_signals"): AnyObj[] {
  const raw = report[key];

  if (!Array.isArray(raw)) return [];

  return raw
    .filter((item) => item && typeof item === "object")
    .map((item, index) => normalizeStory(item, index))
    .filter(isPublishableStory);
}

function isPublishableStory(story: AnyObj): boolean {
  if (!story || typeof story !== "object") return false;

  const title = storyTitle(story, 0);
  const summary = storySummary(story);
  const text = `${title} ${summary}`;

  if (!title) return false;
  if (isBadContent(text)) return false;

  return true;
}

function cleanSignals(items: string[]): string[] {
  return unique(items)
    .filter((item) => !isBadContent(item))
    .slice(0, 6);
}

function buildBriefingItems(stories: AnyObj[], rawSignals: string[]): string[] {
  const fromStories = stories.map((story, index) => {
    const label = storyLabel(story);
    const title = storyTitle(story, index);
    return `${label}: ${title}`;
  });

  return cleanSignals([...fromStories, ...rawSignals]);
}

function spotlightItemsFromStories(stories: AnyObj[]): string[] {
  return cleanSignals(
    stories.map((story, index) => {
      const label = storyLabel(story);
      const title = storyTitle(story, index);
      return `${label}: ${title}`;
    })
  );
}

function removeDoubleLeaguePrefix(value: string): string {
  return value.replace(/^([A-Z][A-Za-z ]+):\s+\1:\s+/i, "$1: ");
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
      <h2 className="mb-3 text-sm font-black uppercase tracking-wide text-red-700">
        {title}
      </h2>
      {children}
    </section>
  );
}

function LineList({ items }: { items: string[] }) {
  const safe = unique(items)
    .map(removeDoubleLeaguePrefix)
    .filter((item) => !isBadContent(item))
    .slice(0, 8);

  if (!safe.length) {
    return (
      <p className="text-sm leading-6 text-neutral-700">
        Monitoring verified betting developments for the next clean newsroom update.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {safe.map((item, i) => (
        <p key={i} className="border-b border-neutral-100 pb-2 text-sm leading-6 text-neutral-800">
          {item}
        </p>
      ))}
    </div>
  );
}

function NewsroomBriefing({ items }: { items: string[] }) {
  const safe = cleanSignals(items).map(removeDoubleLeaguePrefix);

  return (
    <div className="rounded-2xl border border-neutral-300 bg-white p-5 shadow-sm">
      <p className="mb-3 text-xs font-black uppercase tracking-wide text-red-700">
        Live Newsroom Briefing
      </p>

      {safe.length ? (
        <div className="space-y-2">
          {safe.map((item, i) => (
            <p key={i} className="border-b border-neutral-100 pb-2 text-sm leading-6 text-neutral-800">
              {item}
            </p>
          ))}
        </div>
      ) : (
        <p className="text-sm leading-6 text-neutral-700">
          Monitoring verified odds, implied probability, line movement, injuries, weather, totals, spreads and betting market signals.
        </p>
      )}
    </div>
  );
}

function StoryCard({ story, index }: { story: AnyObj; index: number }) {
  const title = removeDoubleLeaguePrefix(storyTitle(story, index));
  const url = storyUrl(story);
  const summary = storySummary(story);
  const label = storyLabel(story);

  const keyData = asList(story.key_data || story.keyData || story.data || story.metrics).filter(
    (item) => !isBadContent(item)
  );

  const why = asList(story.why_it_matters || story.whyItMatters || story.why).filter(
    (item) => !isBadContent(item)
  );

  const watch = asList(story.what_to_watch || story.whatToWatch || story.watch || story.story_angles).filter(
    (item) => !isBadContent(item)
  );

  return (
    <article className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
      <p className="mb-2 text-xs font-black uppercase tracking-wide text-red-700">
        {label}
      </p>

      <h3 className="text-xl font-black leading-tight text-neutral-950">
        <a href={url} target="_blank" rel="noopener noreferrer" className="hover:text-red-700">
          {title}
        </a>
      </h3>

      <p className="mt-3 text-sm leading-6 text-neutral-700">{summary}</p>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-xl bg-neutral-50 p-3">
          <p className="mb-2 text-xs font-black uppercase text-neutral-600">Key Data</p>
          <LineList items={keyData.length ? keyData : [title]} />
        </div>

        <div className="rounded-xl bg-neutral-50 p-3">
          <p className="mb-2 text-xs font-black uppercase text-neutral-600">What The Odds Mean</p>
          <LineList
            items={
              why.length
                ? why
                : ["This betting signal can affect price, value, market direction or reporting priorities."]
            }
          />
        </div>

        <div className="rounded-xl bg-neutral-50 p-3">
          <p className="mb-2 text-xs font-black uppercase text-neutral-600">What To Watch</p>
          <LineList
            items={
              watch.length
                ? watch
                : ["Monitor injury news, lineup updates, weather, totals, spreads and late line movement."]
            }
          />
        </div>
      </div>
    </article>
  );
}

export default function Page() {
  const report = readReport();

  let stories = getStories(report).filter(isPublishableStory);

  const liveNewsroomStories = getSpotlightStories(report, "live_newsroom");
  const editorSignalStories = getSpotlightStories(report, "editor_signals");

  const rawSignals = asList(
    report.key_storylines ||
      report.keyStorylines ||
      report.signals ||
      report.toplines ||
      report.takeaways
  );

  const fallbackHeadline = "Global Betting Report: Live Betting Newsroom Board";

  const headline =
    cleanText(report.headline) && !isBadContent(report.headline)
      ? removeDoubleLeaguePrefix(cleanText(report.headline))
      : fallbackHeadline;

  const snapshot =
    cleanText(report.snapshot) && !isBadContent(report.snapshot)
      ? cleanText(report.snapshot)
      : "A live betting briefing built for bettors tracking odds, implied probability, line movement, injuries, weather and market context.";

  const updated =
    cleanText(report.updated_at) ||
    cleanText(report.generated_at) ||
    cleanText(report.published_at) ||
    "Update time unavailable";

  if (!stories.length) {
    stories = [
      {
        league: "Betting Watch",
        headline,
        summary: snapshot,
        url: DEFAULT_URL,
        key_data: ["Latest betting report generated from the current verified market board."],
        why_it_matters: ["Editors and bettors need quick clarity across odds, totals, spreads and movement."],
        what_to_watch: ["Next verified injury note, weather shift, lineup update or market movement."],
        story_type: "analysis",
      },
    ];
  }

  const leadStories = stories.slice(0, 12);

  const liveBriefingItems = liveNewsroomStories.length
    ? spotlightItemsFromStories(liveNewsroomStories)
    : buildBriefingItems(stories, rawSignals);

  const editorSignalItems = editorSignalStories.length
    ? spotlightItemsFromStories(editorSignalStories)
    : cleanSignals(rawSignals.length ? rawSignals : buildBriefingItems(stories.slice(3), []));

  return (
    <main className="min-h-screen bg-neutral-100 text-neutral-950">
      <div className="border-b border-neutral-800 bg-black text-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-5 py-2 text-xs font-bold uppercase tracking-wide">
          <span className="text-neutral-300">GSR Network:</span>
          {GSR_NETWORK.map(([name, url], index) => (
            <span key={name} className="flex items-center gap-3">
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className={
                  name === "Betting"
                    ? "text-red-300 hover:text-white"
                    : "text-white hover:text-red-300"
                }
              >
                {name}
              </a>
              {index < GSR_NETWORK.length - 1 ? <span className="text-neutral-500">•</span> : null}
            </span>
          ))}
        </div>
      </div>

      <header className="border-b border-neutral-300 bg-white">
        <div className="mx-auto grid max-w-7xl gap-6 px-5 py-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div>
            <p className="text-sm font-black uppercase tracking-wide text-red-700">
              {SITE.name}
            </p>

            <h1 className="mt-3 text-4xl font-black leading-tight md:text-5xl">
              {headline}
            </h1>

            <p className="mt-4 max-w-3xl text-lg leading-8 text-neutral-700">
              {snapshot}
            </p>

            <div className="mt-5 flex flex-wrap gap-3 text-sm font-bold">
              <span className="rounded-full bg-black px-4 py-2 text-white">
                {SITE.tagline}
              </span>
              <span className="rounded-full bg-neutral-200 px-4 py-2 text-neutral-800">
                Updated: {updated}
              </span>
            </div>
          </div>

          <NewsroomBriefing
            items={
              liveBriefingItems.length
                ? liveBriefingItems
                : [
                    "Track the strongest verified betting development on today’s board.",
                    "Prioritize odds movement, injuries, weather, totals and spreads.",
                    "Watch book-to-book differences and late market movement.",
                    "Monitor league-by-league betting angles for reporters and editors.",
                  ]
            }
          />
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl gap-6 px-5 py-6 lg:grid-cols-[0.75fr_1.25fr]">
        <aside className="space-y-6">
          <Block title="Editor Signals">
            <LineList
              items={
                editorSignalItems.length
                  ? editorSignalItems
                  : [
                      "Track the strongest verified betting development on today’s board.",
                      "Prioritize odds movement, injuries, weather, totals and spreads.",
                      "Watch book-to-book differences and late market movement.",
                    ]
              }
            />
          </Block>

          <Block title="Weather Forecast Angle">
            <LineList
              items={[
                "Weather matters most for MLB totals, outdoor football totals, wind-sensitive parks and late game-time market movement.",
                "Watch wind direction, rain risk, temperature, humidity and postponement risk before trusting early totals.",
                "Use verified weather context as a betting signal — not as a standalone pick.",
              ]}
            />

            <a
              href={WEATHER_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 block rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm font-bold text-red-800 hover:bg-red-50"
            >
              Check OddsTrader MLB Weather
            </a>
          </Block>

          <Block title="Journalist Betting Toolkit">
            <div className="space-y-2">
              {TOOLKIT.map(([name, url]) => (
                <a
                  key={name}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm font-bold text-red-800 hover:bg-red-50"
                >
                  {name}
                </a>
              ))}
            </div>
          </Block>

          <Block title="Coverage Lens">
            <LineList
              items={[
                "Market: What number moved, and why might it matter?",
                "Price: Is the favorite getting more expensive or drifting back?",
                "Weather: Could wind, rain, humidity or temperature affect totals?",
                "News: What injury, lineup or roster development could reshape the board?",
                "Context: What do the odds imply about win probability, risk and public perception?",
                "Newsroom: What should journalists verify before publishing betting context?",
              ]}
            />
          </Block>
        </aside>

        <section className="space-y-6">
          {leadStories.map((story, index) => (
            <StoryCard key={story.id || index} story={story} index={index} />
          ))}
        </section>
      </section>

      <footer className="border-t border-neutral-300 bg-white">
        <div className="mx-auto max-w-7xl px-5 py-6">
          <p className="text-sm font-medium text-neutral-700">
            © {new Date().getFullYear()} {SITE.name}. {SITE.tagline}
          </p>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-neutral-500">
            {SITE.descriptor}
          </p>
        </div>
        <EditorialStandard />
      </footer>
    </main>
  );
}