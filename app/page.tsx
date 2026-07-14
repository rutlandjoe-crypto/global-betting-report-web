import fs from "fs";
import path from "path";
import type { Metadata } from "next";

export const dynamic = "force-dynamic";
export const revalidate = 0;
export const fetchCache = "force-no-store";

import EditorialStandard from "@/components/EditorialStandard";
import SocialIconLinks from "@/app/SocialIconLinks";

export const metadata: Metadata = {
  title: "Global Betting Report",
  description:
    "Global Betting Report tracks odds, implied probability, line movement, weather angles, and betting market context.",
};

type AnyObj = Record<string, unknown>;

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
  "out_of_usage_credits",
  "usage quota has been reached",
  "could not load odds",
];

const GENERIC_BETTING_HEADLINE_PHRASES = [
  "late lineup news puts betting markets on watch",
  "futures board tracks roster, injury and schedule news",
  "futures board moves with roster news",
  "markets on watch",
  "futures board tracks",
  "late lineup news",
];

function isNbaSeasonComplete(date = new Date()): boolean {
  const month = date.getMonth() + 1;
  const day = date.getDate();
  return month === 7 || month === 8 || month === 9 || (month === 6 && day >= 17);
}

function isStaleNbaBettingContent(value: unknown): boolean {
  if (!isNbaSeasonComplete()) return false;

  const text = normalizeText(value);
  const staleMarkers = [
    "nba finals",
    "western conference finals",
    "eastern conference finals",
    "game 6",
    "game 7",
    "thunder-spurs",
    "spurs-thunder",
    "oklahoma city thunder at san antonio spurs",
    "san antonio spurs",
    "nba board",
    "nba playoff",
    "nba prices move with injury news",
  ];

  return text.includes("nba") || staleMarkers.some((marker) => text.includes(marker));
}

function isGenericBettingHeadline(value: unknown): boolean {
  const text = normalizeText(value);
  return GENERIC_BETTING_HEADLINE_PHRASES.some((phrase) => text.includes(phrase));
}

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

function cleanText(value: unknown): string {
  if (value === null || value === undefined) return "";

  if (Array.isArray(value)) {
    return value.map(cleanText).filter(Boolean).join(" • ");
  }

  if (typeof value === "object") {
    return Object.values(value).map(cleanText).filter(Boolean).join(" • ");
  }

  return String(value).replace(/\s+/g, " ").trim();
}

function normalizeText(value: unknown): string {
  return cleanText(value).toLowerCase();
}

function isBadContent(value: unknown): boolean {
  const text = normalizeText(value);
  if (!text) return true;
  if (isStaleNbaBettingContent(value)) return true;
  return BAD_CONTENT_PHRASES.some((phrase) => text.includes(phrase));
}

function unique(items: string[]): string[] {
  const seen = new Set<string>();

  return items
    .map((item) => cleanText(item))
    .filter((item) => item && !isBadContent(item))
    .filter((item) => {
      const key = item.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

function asList(value: unknown): string[] {
  if (!value) return [];

  if (Array.isArray(value)) {
    return unique(value.flatMap((item) => asList(item)));
  }

  if (typeof value === "object") {
    return unique(Object.values(value).flatMap((item) => asList(item)));
  }

  return unique(
    String(value)
      .split(/\r?\n|•|Ã¢â‚¬Â¢|\|/)
      .map(cleanText)
      .filter(Boolean)
  );
}

function isValidUrl(value: unknown): boolean {
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

function normalizeSportLabel(value: unknown, fallback = "Betting Watch"): string {
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
  ]);
}

function enrichWhy(story: AnyObj): string[] {
  const direct = asList(story.why_it_matters || story.whyItMatters || story.why);

  return unique([
    ...direct,
    "Betting readers need more than the number â€” they need context on whether price, public money, injuries, matchup edges or weather may be driving the market.",
  ]);
}

function enrichWatch(story: AnyObj): string[] {
  const direct = asList(story.what_to_watch || story.whatToWatch || story.watch);

  return unique([
    ...direct,
    "Watch for injury updates, lineup confirmations, pitching changes, weather shifts, totals movement, spread movement and late sportsbook adjustment.",
  ]);
}

function enrichAngles(story: AnyObj): string[] {
  const direct = asList(story.story_angles || story.storyAngles || story.angles);

  return unique([
    ...direct,
    "Frame the market through price movement, matchup context, public perception, injury timing and late-book adjustment.",
  ]);
}

function normalizeStory(story: AnyObj, index: number, sectionTitle = ""): AnyObj {
  const title = storyTitle(story, index);
  const rawLabel = story.league || story.sport || story.category || story.label || sectionTitle || story.title;
  const label = normalizeSportLabel(rawLabel, "Betting Watch");

  return {
    ...story,
    id: cleanText(story.id || story.key || `${label}-${index}`),
    key: cleanText(story.key || story.id || `${label}-${index}`),
    league: label,
    label,
    title,
    headline: title,
    summary: storySummary(story),
    snapshot: storySummary(story),
    url: storyUrl(story),
    key_data: enrichKeyData(story, title),
    why_it_matters: enrichWhy(story),
    what_to_watch: enrichWatch(story),
    story_angles: enrichAngles(story),
  };
}

function sectionToStories(section: AnyObj, index: number): AnyObj[] {
  const sectionTitle = normalizeSportLabel(
    section.title || section.league || section.sport || `Section ${index + 1}`
  );

  const cards = section.homepage_cards || section.cards || section.items || section.stories;

  if (Array.isArray(cards) && cards.length) {
    const objectCards = cards.filter((card: unknown) => card && typeof card === "object");
    const stringCards = cards.filter((card: unknown) => typeof card === "string");

    if (objectCards.length) {
      return objectCards.map((card, cardIndex: number) =>
        normalizeStory(card as AnyObj, cardIndex, sectionTitle)
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
            story_angles: [
              "Identify whether the betting angle comes from pricing, injuries, weather, public perception or matchup context.",
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
        story_angles: asList(section.story_angles || section.storyAngles || section.angles),
        url: extractBestUrl(section),
      },
      index,
      sectionTitle
    ),
  ];
}

function normalizeCollection(candidates: unknown, sourceName: string): AnyObj[] {
  if (Array.isArray(candidates) && candidates.length) {
    return candidates
      .filter((story) => story && typeof story === "object")
      .map((story, index) =>
        normalizeStory(
          {
            ...(story as AnyObj),
            source_collection: sourceName,
          },
          index
        )
      );
  }

  if (candidates && typeof candidates === "object") {
    return Object.entries(candidates).flatMap(([key, value]: [string, any], index) => {
      if (Array.isArray(value)) {
        return value
          .filter((story) => story && typeof story === "object")
          .map((story, itemIndex) =>
            normalizeStory(
              {
                id: `${key}-${itemIndex}`,
                key,
                league: key,
                source_collection: sourceName,
                ...(story as AnyObj),
              },
              itemIndex
            )
          );
      }

      if (value && typeof value === "object") {
        return [
          normalizeStory(
            {
              id: key,
              key,
              league: key,
              source_collection: sourceName,
              ...value,
            },
            index
          ),
        ];
      }

      return [];
    });
  }

  return [];
}

function getStories(report: AnyObj): AnyObj[] {
  const publicCollections: [string, unknown][] = [
    ["homepage_cards", report.homepage_cards],
    ["live_newsroom", report.live_newsroom],
    ["stories", report.stories],
    ["cards", report.cards],
    ["news", report.news],
    ["headlines", report.headlines],
    ["items", report.items],
    ["articles", report.articles],
  ];

  for (const [sourceName, candidates] of publicCollections) {
    const normalized = normalizeCollection(candidates, sourceName).filter(isPublishableStory);
    if (normalized.length) return normalized;
  }

  if (Array.isArray(report.sections) && report.sections.length) {
    return report.sections.flatMap((section: AnyObj, index: number) =>
      sectionToStories(section || {}, index)
    );
  }

  if (report.sections && typeof report.sections === "object") {
    return Object.values(report.sections).flatMap((section: any, index: number) =>
      sectionToStories(section || {}, index)
    );
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
  if (isGenericBettingHeadline(title)) return false;

  return true;
}

function storyPriority(story: AnyObj): number {
  const text = normalizeText([
    story.league,
    story.headline,
    story.title,
    story.game,
    story.snapshot,
    story.market,
  ]);

  if (isStaleNbaBettingContent(text)) return -100;
  if (text.includes("world cup")) return 100;
  if (text.includes("mlb") || text.includes("baseball")) return 90;
  if (text.includes("nfl")) return 30;
  if (text.includes("partner") || text.includes("oddstrader")) return 20;
  return 10;
}

function cleanFallbackStory(updated: string): AnyObj {
  return {
    league: "Betting Watch",
    headline: "OddsTrader MLB weather board gives bettors a cleaner totals read",
    summary:
      "A clean partner and data-tool headline is being used because no strong MLB or World Cup betting story is available.",
    snapshot:
      "A clean partner and data-tool headline is being used because no strong MLB or World Cup betting story is available.",
    url: WEATHER_URL,
    key_data: ["Partner/tool angle: MLB weather and totals context."],
    why_it_matters: [
      "Weather is context, not a pick; the betting read still needs current prices and game-day confirmation.",
    ],
    what_to_watch: [
      "Wind, rain risk, temperature, humidity, starting pitchers and late total movement.",
    ],
    story_angles: ["Frame the market through weather, pitching, totals and current sportsbook prices."],
    story_type: "partner_context",
    updated_at: updated,
  };
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
    <section className="rounded-2xl border border-lime-300/40 bg-slate-950 p-5 shadow-sm shadow-lime-500/10">
      <h2 className="mb-3 text-sm font-black uppercase tracking-wide text-lime-300">
        {title}
      </h2>
      {children}
    </section>
  );
}

function EditorsBookshelf() {
  const books = [
    ["Sharp Sports Betting", "Stanford Wong"],
    ["The Logic of Sports Betting", "Ed Miller & Matthew Davidow"],
    ["Trading Bases", "Joe Peta"],
  ];

  return (
    <Block title="Editor's Bookshelf">
      <div className="space-y-2">
        {books.map(([title, author]) => (
          // TODO: Replace this Amazon search URL with the final Amazon Associates URL.
          <a
            key={title}
            href={`https://www.amazon.com/s?k=${encodeURIComponent(`${title} ${author}`)}&tag=gsrbetting-20`}
            target="_blank"
            rel="sponsored noopener noreferrer"
            className="block rounded-xl border border-lime-300/30 bg-black/40 px-4 py-3 hover:border-lime-200"
          >
            <span className="block text-sm font-bold text-lime-200">{title}</span>
            <span className="mt-1 block text-xs text-slate-400">{author}</span>
          </a>
        ))}
      </div>
      <p className="mt-3 text-xs leading-5 text-slate-400">
        As an Amazon Associate, GSR Network earns from qualifying purchases.
      </p>
    </Block>
  );
}

function LineList({ items }: { items: string[] }) {
  const safe = unique(items)
    .map(removeDoubleLeaguePrefix)
    .filter((item) => !isBadContent(item))
    .slice(0, 8);

  if (!safe.length) {
    return (
      <p className="text-sm leading-6 text-slate-300">
        Monitoring verified betting developments for the next clean newsroom update.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {safe.map((item, i) => (
        <p key={i} className="border-b border-slate-800 pb-2 text-sm leading-6 text-slate-200">
          {item}
        </p>
      ))}
    </div>
  );
}

function expandBettingLines(items: string[]): string[] {
  return unique(
    items.flatMap((item) =>
      cleanText(item)
        .replace(/\s+Market read:\s*/i, "\n")
        .replace(/\s+-\s+(?=[A-Z])/g, "\n")
        .split(/\r?\n/)
        .map(cleanText)
        .filter(Boolean)
    )
  );
}

function DetailBlock({ title, items }: { title: string; items: string[] }) {
  const safe = expandBettingLines(items)
    .map(removeDoubleLeaguePrefix)
    .filter((item) => !isBadContent(item))
    .slice(0, 5);

  if (!safe.length) return null;

  return (
    <div className="rounded-xl border border-slate-800 bg-black/40 p-3">
      <p className="mb-2 text-xs font-black uppercase text-lime-300">{title}</p>
      <LineList items={safe} />
    </div>
  );
}

function NewsroomBriefing({ items }: { items: string[] }) {
  const safe = cleanSignals(items).map(removeDoubleLeaguePrefix);

  return (
    <div className="rounded-2xl border border-lime-300/50 bg-slate-950 p-5 shadow-sm shadow-lime-500/20">
      <p className="mb-3 text-xs font-black uppercase tracking-wide text-lime-300">
        Live Newsroom Briefing
      </p>

      {safe.length ? (
        <div className="space-y-2">
          {safe.map((item, i) => (
            <p key={i} className="border-b border-slate-800 pb-2 text-sm leading-6 text-slate-200">
              {item}
            </p>
          ))}
        </div>
      ) : (
        <p className="text-sm leading-6 text-slate-300">
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
  const game = cleanText(story.game) || title;

  const market = expandBettingLines([
    cleanText(story.market),
    cleanText(story.bookmaker) ? `Bookmaker: ${cleanText(story.bookmaker)}` : "",
    cleanText(story.moneyline) ? `Moneyline: ${cleanText(story.moneyline)}` : "",
    cleanText(story.spread) ? `Spread: ${cleanText(story.spread)}` : "",
    cleanText(story.total) ? `Total: ${cleanText(story.total)}` : "",
    ...asList(story.key_data || story.keyData || story.data || story.metrics),
  ]).filter((item) => !isBadContent(item));

  const impliedProbability = expandBettingLines([
    cleanText(story.implied_probability || story.impliedProbability),
    ...market.filter((item) => item.toLowerCase().includes("implied probability")),
    ...asList(summary).filter((item) => item.toLowerCase().includes("implied probability")),
  ]).filter((item) => !isBadContent(item));

  const why = asList(story.why_it_matters || story.whyItMatters || story.why).filter(
    (item) => !isBadContent(item)
  );

  const watch = asList(story.what_to_watch || story.whatToWatch || story.watch).filter(
    (item) => !isBadContent(item)
  );

  const angles = asList(story.story_angles || story.storyAngles || story.angles).filter(
    (item) => !isBadContent(item)
  );

  return (
    <article className="rounded-2xl border border-slate-800 bg-slate-950 p-5 shadow-sm shadow-lime-500/10">
      <p className="mb-2 text-xs font-black uppercase tracking-wide text-lime-300">
        {label}
      </p>

      <h3 className="text-xl font-black leading-tight text-white">
        <a href={url} target="_blank" rel="noopener noreferrer" className="hover:text-lime-300">
          {title}
        </a>
      </h3>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <DetailBlock title="Game" items={[game]} />
        <DetailBlock title="Market" items={market.length ? market : asList(summary)} />
        <DetailBlock
          title="Implied Probability"
          items={
            impliedProbability.length
              ? impliedProbability
              : ["Monitor the moneyline to estimate the market's implied win probability."]
          }
        />
        <DetailBlock
          title="Why It Matters"
          items={
            why.length
              ? why
              : ["This betting signal can affect price, value, market direction or reporting priorities."]
          }
        />
        <DetailBlock
          title="What To Watch"
          items={
            watch.length
              ? watch
              : ["Monitor injury news, lineup updates, weather, totals, spreads and late line movement."]
          }
        />
        <DetailBlock
          title="Story Angles"
          items={
            angles.length
              ? angles
              : ["Frame the market through price movement, matchup context, public perception, injury timing and late-book adjustment."]
          }
        />
      </div>
    </article>
  );
}


function SponsorPlacementBlock() {
  return (
    <section className="mx-auto max-w-7xl px-5 py-3">
      <div className="rounded-2xl border border-black/10 bg-white/90 p-5 shadow-sm">
        <p className="text-xs font-black uppercase tracking-[0.25em] text-neutral-500">
          Partner Spotlight
        </p>
        <h2 className="mt-2 text-xl font-black">
          Partnership opportunities are available across the GSR Network.
        </h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-700">
          Reach readers through clean, clearly labeled placements across Sports, Betting, AI, Politics and Entertainment — built around journalistic integrity.
        </p>
      </div>
    </section>
  );
}

function AdvertiseWithGsrBlock() {
  return (
    <section className="mx-auto max-w-7xl px-5 py-6">
      <div className="rounded-2xl border border-black/10 bg-white/90 p-5 shadow-sm">
        <p className="text-xs font-black uppercase tracking-[0.25em] text-neutral-500">
          Advertise With GSR Network
        </p>
        <h2 className="mt-2 text-xl font-black">
          Sponsorship, partnership, affiliate and custom campaign opportunities are open.
        </h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-700">
          GSR Network offers clearly labeled placements for brands, events, data companies, media partners and vertical-specific advertisers across all five platforms.
        </p>
      </div>
    </section>
  );
}

export default function Page() {
  const report = readReport();

  let stories = getStories(report)
    .filter(isPublishableStory)
    .sort((a, b) => storyPriority(b) - storyPriority(a));

  const liveNewsroomStories = getSpotlightStories(report, "live_newsroom");
  const editorSignalStories = getSpotlightStories(report, "editor_signals");

  const rawSignals = asList(
    report.key_storylines ||
      report.keyStorylines ||
      report.signals ||
      report.toplines ||
      report.takeaways
  );

  const updated =
    cleanText(report.updated_at) ||
    cleanText(report.generated_at) ||
    cleanText(report.published_at) ||
    "Update time unavailable";

  if (!stories.length) {
    stories = [cleanFallbackStory(updated)];
  }

  const leadStories = stories.slice(0, 12);
  const leadStory = leadStories[0] || cleanFallbackStory(updated);
  const fallbackHeadline = "Global Betting Report: Live Betting Newsroom Board";

  const headline = removeDoubleLeaguePrefix(
    cleanText(storyTitle(leadStory, 0)) ||
      (cleanText(report.headline) && !isBadContent(report.headline)
        ? cleanText(report.headline)
        : fallbackHeadline)
  );

  const snapshot =
    cleanText(leadStory.snapshot || leadStory.summary) && !isBadContent(leadStory.snapshot || leadStory.summary)
      ? cleanText(leadStory.snapshot || leadStory.summary)
      : cleanText(report.snapshot) && !isBadContent(report.snapshot)
        ? cleanText(report.snapshot)
        : "A live betting briefing built for bettors tracking odds, implied probability, line movement, injuries, weather and market context.";

  const liveBriefingItems = liveNewsroomStories.length
    ? spotlightItemsFromStories(liveNewsroomStories)
    : buildBriefingItems(stories, rawSignals);

  const editorSignalItems = editorSignalStories.length
    ? spotlightItemsFromStories(editorSignalStories)
    : cleanSignals(rawSignals.length ? rawSignals : buildBriefingItems(stories.slice(3), []));

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="border-b border-lime-300/30 bg-black text-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-5 py-2 text-xs font-bold uppercase tracking-wide">
          <span className="text-slate-400">GSR Network:</span>
          {GSR_NETWORK.map(([name, url], index) => (
            <span key={name} className="flex items-center gap-3">
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className={
                  name === "Betting"
                    ? "text-lime-300 hover:text-white"
                    : "text-white hover:text-lime-300"
                }
              >
                {name}
              </a>
              {index < GSR_NETWORK.length - 1 ? <span className="text-slate-600">•</span> : null}
            </span>
          ))}
        </div>
      </div>

      <div className="border-b border-neutral-800 bg-neutral-950 text-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-5 py-2 text-xs font-bold uppercase tracking-wide">
          <span className="text-neutral-400">Follow GSR:</span>
          <SocialIconLinks hoverClassName="hover:border-lime-300" />
        </div>
      </div>

      <header className="border-b border-lime-300/20 bg-gradient-to-br from-black via-slate-950 to-emerald-950">
        <div className="mx-auto grid max-w-7xl gap-6 px-5 py-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div>
            <p className="text-sm font-black uppercase tracking-wide text-lime-300">
              {SITE.name}
            </p>

            <h1 className="mt-3 text-4xl font-black leading-tight text-white md:text-5xl">
              {headline}
            </h1>

            <p className="mt-4 max-w-3xl text-lg leading-8 text-slate-300">
              {snapshot}
            </p>

            <div className="mt-5 flex flex-wrap gap-3 text-sm font-bold">
              <span className="rounded-full bg-lime-300 px-4 py-2 text-black">
                {SITE.tagline}
              </span>
              <span className="rounded-full border border-lime-300/30 bg-black px-4 py-2 text-lime-200">
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
      <EditorialStandard />
      <SponsorPlacementBlock />


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
                "Use verified weather context as a betting signal â€” not as a standalone pick.",
              ]}
            />

            <a
              href={WEATHER_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 block rounded-xl border border-lime-300/40 bg-lime-300 px-4 py-3 text-sm font-black text-black hover:bg-lime-200"
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
                  className="block rounded-xl border border-lime-300/30 bg-black/40 px-4 py-3 text-sm font-bold text-lime-200 hover:bg-lime-300 hover:text-black"
                >
                  {name}
                </a>
              ))}
            </div>
          </Block>

          <EditorsBookshelf />

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
            <StoryCard key={cleanText(story.id) || index} story={story} index={index} />
          ))}
        </section>
      </section>
      <AdvertiseWithGsrBlock />


      <footer className="border-t border-lime-300/20 bg-black">
        <div className="mx-auto max-w-7xl px-5 py-6">
          <p className="text-sm font-medium text-lime-200">
            Â© {new Date().getFullYear()} {SITE.name}. {SITE.tagline}
          </p>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-400">
            {SITE.descriptor}
          </p>
        </div>
      </footer>
    </main>
  );
}

