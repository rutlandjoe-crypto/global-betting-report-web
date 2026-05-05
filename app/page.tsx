import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";
export const revalidate = 0;
export const fetchCache = "force-no-store";

import EditorialStandard from "@/components/EditorialStandard";

type AnyObj = Record<string, any>;

const SITE = {
  name: "Global Sports Report",
  tagline: "Built for journalists, by a journalist.",
  topic: "Sports",
  descriptor:
    "Global Sports Report tracks live scores, schedules, advanced metrics, story angles and newsroom-ready sports intelligence across MLB, NBA, NFL, NHL, soccer and the broader sports calendar.",
};

const TOOLKIT = [
  ["ESPN", "https://www.espn.com/"],
  ["The Athletic", "https://www.nytimes.com/athletic/"],
  ["Sports Reference", "https://www.sports-reference.com/"],
  ["Baseball Savant", "https://baseballsavant.mlb.com/"],
  ["Spotrac", "https://www.spotrac.com/"],
];

const GSR_NETWORK = [
  ["Sports", "https://globalsportsreport.com"],
  ["AI", "https://globalaireport.news"],
  ["Politics", "https://globalpoliticsreport.com"],
  ["Entertainment", "https://globalentertainmentreport.com"],
];

const LEAGUE_LABELS: AnyObj = {
  breaking_news: "Breaking Sports News",
  mlb: "MLB",
  nba: "NBA",
  nhl: "NHL",
  nfl: "NFL",
  ncaafb: "College Football",
  soccer: "Soccer",
  betting_odds: "Betting Odds",
  fantasy: "Fantasy",
};

const LEAGUE_DEFAULT_URLS: AnyObj = {
  breaking_news: "https://www.espn.com/",
  mlb: "https://www.espn.com/mlb/",
  nba: "https://www.espn.com/nba/",
  nhl: "https://www.espn.com/nhl/",
  nfl: "https://www.espn.com/nfl/",
  ncaafb: "https://www.espn.com/college-football/",
  soccer: "https://www.espn.com/soccer/",
  betting_odds: "https://www.espn.com/",
  fantasy: "https://www.espn.com/fantasy/",
};

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
];

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
        .split(/\n|•|\|/)
        .map((x) => x.trim())
        .filter(Boolean)
    );
  }

  if (typeof value === "object") {
    return Object.values(value).flatMap((item) =>
      cleanText(item)
        .split(/\n|•|\|/)
        .map((x) => x.trim())
        .filter(Boolean)
    );
  }

  return cleanText(value)
    .split(/\n|•|\|/)
    .map((x) => x.trim())
    .filter(Boolean);
}

function isValidUrl(value: any): boolean {
  const url = cleanText(value);
  return url.startsWith("http://") || url.startsWith("https://");
}

function findUrlInText(value: any): string {
  const text = cleanText(value);
  const match = text.match(/https?:\/\/[^\s"'<>]+/);
  return match ? match[0].replace(/[),.;]+$/, "") : "";
}

function extractBestUrl(section: AnyObj, key: string): string {
  const directCandidates = [
    section.url,
    section.link,
    section.source_url,
    section.sourceUrl,
    section.href,
    section.web_url,
    section.webUrl,
  ];

  for (const candidate of directCandidates) {
    if (isValidUrl(candidate)) return cleanText(candidate);
  }

  if (Array.isArray(section.links)) {
    for (const link of section.links) {
      if (typeof link === "string" && isValidUrl(link)) return cleanText(link);
      if (link && typeof link === "object") {
        const candidates = [link.url, link.href, link.link, link.source_url];
        for (const candidate of candidates) {
          if (isValidUrl(candidate)) return cleanText(candidate);
        }
      }
    }
  }

  const textSources = [
    section.content,
    section.summary,
    section.snapshot,
    section.description,
    section.key_storylines,
    section.advanced,
    section.final_scores,
    section.live_games,
    section.upcoming,
  ];

  for (const source of textSources) {
    const found = findUrlInText(source);
    if (found) return found;
  }

  return LEAGUE_DEFAULT_URLS[key] || "https://www.espn.com/";
}

function extractSectionLines(content: string, heading: string): string[] {
  if (!content) return [];

  const lines = content.split("\n");
  const startIndex = lines.findIndex(
    (line) => line.trim().toUpperCase() === heading.toUpperCase()
  );

  if (startIndex === -1) return [];

  const output: string[] = [];

  for (let i = startIndex + 1; i < lines.length; i++) {
    const line = lines[i].trim();

    if (!line) continue;

    const isNextHeading =
      /^[A-Z0-9\s&/()-]{4,}$/.test(line) &&
      !line.includes(".") &&
      !line.includes(":");

    if (isNextHeading) break;

    output.push(line.replace(/^- /, "").trim());
  }

  return output.filter(Boolean);
}

function extractHeadline(section: AnyObj): string {
  const headlineLines = extractSectionLines(section.content || "", "HEADLINE");

  return (
    cleanText(section.headline) ||
    cleanText(headlineLines[0]) ||
    cleanText(section.title) ||
    "Sports newsroom update"
  );
}

function extractSnapshot(section: AnyObj): string {
  const snapshotLines = extractSectionLines(section.content || "", "SNAPSHOT");

  return (
    cleanText(section.snapshot) ||
    cleanText(snapshotLines[0]) ||
    cleanText(section.content).slice(0, 260) ||
    "Latest verified sports report generated for newsroom review."
  );
}

function sectionToStory(key: string, section: AnyObj): AnyObj {
  const content = section.content || "";

  const keyData = [
    ...extractSectionLines(content, "KEY DATA POINTS"),
    ...asList(section.key_storylines),
    ...asList(section.final_scores),
    ...asList(section.live_games),
    ...asList(section.upcoming),
    ...asList(section.advanced?.sections?.key_data_points),
    ...asList(section.advanced?.sections?.matchup_flags),
    ...asList(section.advanced),
  ];

  const why = [
    ...extractSectionLines(content, "WHY IT MATTERS"),
    ...asList(section.advanced?.sections?.why_it_matters),
    ...asList(section.why_it_matters),
  ];

  const watch = [
    ...extractSectionLines(content, "STORY ANGLES"),
    ...extractSectionLines(content, "LIVE"),
    ...extractSectionLines(content, "UPCOMING"),
    ...extractSectionLines(content, "FINAL SCORES"),
    ...asList(section.advanced?.sections?.story_angles),
    ...asList(section.advanced?.sections?.statcast_watch),
    ...asList(section.advanced?.sections?.league_efficiency_watch),
    ...asList(section.story_angles),
    ...asList(section.what_to_watch),
  ];

  return {
    id: key,
    key,
    league: section.title || LEAGUE_LABELS[key] || key.toUpperCase(),
    title: section.title || LEAGUE_LABELS[key] || key.toUpperCase(),
    headline: extractHeadline(section),
    summary: extractSnapshot(section),
    snapshot: extractSnapshot(section),
    updated_at: section.updated_at,
    source_file: section.source_file,
    url: extractBestUrl(section, key),
    key_data: unique(keyData).filter((item) => !isBadContent(item)).slice(0, 5),
    why_it_matters: unique(why).filter((item) => !isBadContent(item)).slice(0, 5),
    what_to_watch: unique(watch).filter((item) => !isBadContent(item)).slice(0, 6),
    story_type: section.story_type || "analysis",
    priority_score: section.priority_score || 0,
  };
}

function normalizeStory(story: AnyObj, index: number): AnyObj {
  const key = cleanText(story.key || story.id || story.league || `story-${index}`);
  const title = cleanText(story.title || story.league || LEAGUE_LABELS[key] || "Sports Watch");
  const url = extractBestUrl(story, key);

  return {
    ...story,
    id: key || `story-${index}`,
    key,
    league: title,
    title,
    headline: cleanText(story.headline || story.title || story.name),
    summary: cleanText(story.summary || story.snapshot || story.description || story.body),
    snapshot: cleanText(story.snapshot || story.summary || story.description || story.body),
    url,
  };
}

function getStories(report: AnyObj): AnyObj[] {
  if (Array.isArray(report.sections) && report.sections.length) {
    return report.sections.map((section: AnyObj, index: number) =>
      sectionToStory(section.key || section.id || `section-${index}`, section || {})
    );
  }

  if (report.sections && typeof report.sections === "object") {
    return Object.entries(report.sections).map(([key, value]: [string, any]) =>
      sectionToStory(key, value || {})
    );
  }

  const candidates =
    report.homepage_cards ||
    report.cards ||
    report.stories ||
    report.news ||
    report.headlines ||
    report.items ||
    report.articles ||
    null;

  if (Array.isArray(candidates) && candidates.length) {
    return candidates
      .filter((story) => story && typeof story === "object")
      .map((story, index) => normalizeStory(story, index));
  }

  if (candidates && typeof candidates === "object") {
    return Object.entries(candidates).map(([key, value]: [string, any], index) => {
      if (value && typeof value === "object") {
        return normalizeStory(
          {
            id: key,
            key,
            league: value.league || LEAGUE_LABELS[key] || key.toUpperCase(),
            ...value,
          },
          index
        );
      }

      return normalizeStory(
        {
          id: key,
          key,
          league: LEAGUE_LABELS[key] || key.toUpperCase(),
          headline: cleanText(value),
        },
        index
      );
    });
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

function storyTitle(story: AnyObj, index: number): string {
  return (
    cleanText(story.headline) ||
    cleanText(story.title) ||
    cleanText(story.name) ||
    cleanText(story.league) ||
    `Sports Storyline ${index + 1}`
  );
}

function storyUrl(story: AnyObj): string {
  const url = cleanText(story.url) || cleanText(story.link) || cleanText(story.source_url);
  return isValidUrl(url) ? url : "https://www.espn.com/";
}

function storySummary(story: AnyObj): string {
  return (
    cleanText(story.snapshot) ||
    cleanText(story.summary) ||
    cleanText(story.description) ||
    cleanText(story.body) ||
    "Sports development flagged for newsroom monitoring."
  );
}

function storyLabel(story: AnyObj): string {
  return cleanText(story.league) || cleanText(story.title) || cleanText(story.label) || "Sports Watch";
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
    .filter((item) => !isBadContent(item))
    .slice(0, 8);

  if (!safe.length) {
    return (
      <p className="text-sm leading-6 text-neutral-700">
        Monitoring verified developments for the next clean newsroom update.
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
  const safe = cleanSignals(items);

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
          Monitoring verified scores, injuries, playoff movement, roster changes and advanced performance signals.
        </p>
      )}
    </div>
  );
}

function StoryCard({ story, index }: { story: AnyObj; index: number }) {
  const title = storyTitle(story, index);
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
          <p className="mb-2 text-xs font-black uppercase text-neutral-600">Why It Matters</p>
          <LineList
            items={
              why.length
                ? why
                : ["This development can affect coverage priorities, follow-up angles or newsroom planning."]
            }
          />
        </div>

        <div className="rounded-xl bg-neutral-50 p-3">
          <p className="mb-2 text-xs font-black uppercase text-neutral-600">What To Watch</p>
          <LineList
            items={
              watch.length
                ? watch
                : ["Monitor confirmed reporting, next-game context, injury updates, standings movement or metric shifts."]
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

  const fallbackHeadline = "Global Sports Report: Live Sports Newsroom Board";

  const headline =
    cleanText(report.headline) && !isBadContent(report.headline)
      ? cleanText(report.headline)
      : fallbackHeadline;

  const snapshot =
    cleanText(report.snapshot) && !isBadContent(report.snapshot)
      ? cleanText(report.snapshot)
      : "A live sports briefing built for journalists tracking verified scores, results, analytics, playoff races, injuries and story angles.";

  const updated =
    cleanText(report.updated_at) ||
    cleanText(report.generated_at) ||
    cleanText(report.published_at) ||
    "Update time unavailable";

  if (!stories.length) {
    stories = [
      {
        league: "Sports Watch",
        headline,
        summary: snapshot,
        url: "https://www.espn.com/",
        key_data: ["Latest sports report generated from the current verified newsroom board."],
        why_it_matters: ["Editors need fast clarity across scores, results, analytics and live story movement."],
        what_to_watch: ["Next verified result, injury note, roster move, playoff angle or advanced metric signal."],
        story_type: "analysis",
      },
    ];
  }

  const leadStories = stories.slice(0, 10);

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
                className="text-white hover:text-red-300"
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
                    "Track the strongest verified sports development on today’s board.",
                    "Prioritize results, injuries, playoff movement, roster news and verified links.",
                    "Watch advanced metrics, standings shifts and late-breaking league updates.",
                    "Monitor league-by-league angles for reporters and editors.",
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
                      "Track the strongest verified sports development on today’s board.",
                      "Prioritize results, injuries, playoff movement, roster news and verified links.",
                      "Watch advanced metrics, standings shifts and late-breaking league updates.",
                    ]
              }
            />
          </Block>

          <Block title="Journalist Toolkit">
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
                "Scoreboard: What result changes the day’s sports conversation?",
                "News: What injury, roster, playoff or league development needs follow-up?",
                "Performance: Which player or team metric deserves deeper reporting?",
                "Context: What standings, playoff or roster angle matters most?",
                "Newsroom: What should journalists verify next?",
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