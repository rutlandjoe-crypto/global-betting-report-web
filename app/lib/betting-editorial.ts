import fs from "fs";
import path from "path";

export type BettingStory = {
  slug: string;
  title: string;
  label: string;
  summary: string;
  sourceUrl: string;
  updatedAt: string;
  game: string;
  market: string[];
  impliedProbability: string[];
  whyItMatters: string[];
  whatToWatch: string[];
  storyAngles: string[];
};

type AnyObj = Record<string, unknown>;

function cleanText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.map(cleanText).filter(Boolean).join(" • ");
  if (typeof value === "object") return Object.values(value).map(cleanText).filter(Boolean).join(" • ");
  return String(value).replace(/\s+/g, " ").trim();
}

function asList(value: unknown): string[] {
  if (!value) return [];
  if (Array.isArray(value)) return value.flatMap(asList).filter(Boolean);
  if (typeof value === "object") return Object.values(value).flatMap(asList).filter(Boolean);
  return String(value).split(/\r?\n|•|\|/).map(cleanText).filter(Boolean);
}

function readReport(): AnyObj {
  try {
    const file = path.join(process.cwd(), "public", "latest_report.json");
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return {};
  }
}

function slugify(value: string, index: number): string {
  const slug = value
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^\w\s-]/g, "")
    .replace(/[\s_]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 90);

  return slug || `betting-story-${index + 1}`;
}

function extractUrl(story: AnyObj): string {
  const candidates = [
    story.url,
    story.link,
    story.source_url,
    story.sourceUrl,
    story.href,
    story.web_url,
    story.webUrl,
  ];

  for (const candidate of candidates) {
    const value = cleanText(candidate);
    if (value.startsWith("http://") || value.startsWith("https://")) return value;
  }

  return "";
}

function normalize(story: AnyObj, index: number, updatedAt: string): BettingStory {
  const title =
    cleanText(story.headline) ||
    cleanText(story.title) ||
    cleanText(story.name) ||
    `Betting Story ${index + 1}`;

  const summary =
    cleanText(story.snapshot) ||
    cleanText(story.summary) ||
    cleanText(story.description) ||
    cleanText(story.why_it_matters) ||
    cleanText(story.body);

  const label =
    cleanText(story.league) ||
    cleanText(story.sport) ||
    cleanText(story.category) ||
    "Betting";

  const market = [
    cleanText(story.market),
    cleanText(story.bookmaker) ? `Bookmaker: ${cleanText(story.bookmaker)}` : "",
    cleanText(story.moneyline) ? `Moneyline: ${cleanText(story.moneyline)}` : "",
    cleanText(story.spread) ? `Spread: ${cleanText(story.spread)}` : "",
    cleanText(story.total) ? `Total: ${cleanText(story.total)}` : "",
    ...asList(story.key_data || story.keyData || story.data || story.metrics),
  ].filter(Boolean);

  return {
    slug: slugify(title, index),
    title,
    label,
    summary,
    sourceUrl: extractUrl(story),
    updatedAt,
    game: cleanText(story.game) || title,
    market,
    impliedProbability: asList(story.implied_probability || story.impliedProbability),
    whyItMatters: asList(story.why_it_matters || story.whyItMatters || story.why),
    whatToWatch: asList(story.what_to_watch || story.whatToWatch || story.watch),
    storyAngles: asList(story.story_angles || story.storyAngles || story.angles),
  };
}

export function getBettingStories(): BettingStory[] {
  const report = readReport();

  const updatedAt =
    cleanText(report.updated_at) ||
    cleanText(report.generated_at) ||
    cleanText(report.published_at) ||
    "";

  const collections = [
    report.homepage_cards,
    report.live_newsroom,
    report.stories,
    report.cards,
    report.news,
    report.headlines,
    report.items,
    report.articles,
  ];

  for (const value of collections) {
    if (Array.isArray(value) && value.length) {
      return value
        .filter((item) => item && typeof item === "object")
        .map((item, index) => normalize(item as AnyObj, index, updatedAt))
        .slice(0, 24);
    }
  }

  return [];
}

export function getBettingStory(slug: string) {
  return getBettingStories().find((story) => story.slug === slug);
}

export function getBettingLastModified(): Date {
  const value = getBettingStories()[0]?.updatedAt;
  const date = value ? new Date(value) : null;

  return date && !Number.isNaN(date.getTime())
    ? date
    : new Date("2026-01-01T00:00:00.000Z");
}
