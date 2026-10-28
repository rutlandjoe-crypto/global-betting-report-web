type Item = Record<string, unknown>;
type Reading = { title: string; slug: string; reportDate: string };

function items(value: unknown): Item[] {
  return Array.isArray(value)
    ? value.filter((item): item is Item => !!item && typeof item === "object")
    : [];
}

/** Adapt only the app response; the website's section schema stays intact. */
export function bettingAppReport(report: Item, readings: Reading[]): Item {
  const date = String(report.updated_at || report.generated_at || "").slice(0, 10);
  const destinations = new Map(
    readings.filter((story) => story.reportDate === date)
      .map((story) => [story.title, `https://www.globalbettingreport.com/editorial/${story.slug}`]),
  );
  const adapt = (card: Item): Item => {
    const destination = destinations.get(String(card.headline || card.title || ""));
    const original = String(card.url || "");
    // An unmatched scoreboard is not an article. Keep its source separately
    // rather than presenting it as a working "Read Full Story" destination.
    return {
      ...card,
      source_name: card.source_name || card.source_label || card.source || "",
      url: destination || (original.includes("/scoreboard") ? "" : original),
    };
  };
  const sections = report.sections;
  const flattened = Array.isArray(sections) ? items(sections)
    : sections && typeof sections === "object"
      ? Object.values(sections).flatMap((section) => {
          if (!section || typeof section !== "object") return [];
          const group = section as Item;
          return Array.isArray(group.cards) ? items(group.cards) : [group];
        }) : [];
  return {
    ...report,
    homepage_cards: items(report.homepage_cards).map(adapt),
    live_newsroom: items(report.live_newsroom).map(adapt),
    sections: flattened.map(adapt),
  };
}
