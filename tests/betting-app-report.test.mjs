import assert from "node:assert/strict";
import test from "node:test";
import { bettingAppReport } from "../app/lib/betting-app-report.ts";

test("app sections are arrays and same-date market reports open their own pages", () => {
  const card = { headline: "Away at Home", url: "https://www.espn.com/nfl/scoreboard", source_label: "The Odds API v4" };
  const report = { updated_at: "2026-10-27T18:00:00Z", homepage_cards: [card], live_newsroom: [card], sections: { nfl: { cards: [card] } } };
  const output = bettingAppReport(report, [{ title: card.headline, slug: "2026-10-27-away-at-home", reportDate: "2026-10-27" }]);
  for (const key of ["sections", "homepage_cards", "live_newsroom"]) {
    assert.ok(Array.isArray(output[key]));
    assert.equal(output[key][0].url, "https://www.globalbettingreport.com/editorial/2026-10-27-away-at-home");
    assert.equal(output[key][0].source_name, "The Odds API v4");
  }
  assert.equal(report.homepage_cards[0].url, card.url);
  assert.ok(!Array.isArray(report.sections));
});

test("source article URLs are retained and old readings cannot replace a new report", () => {
  const news = { headline: "Original source headline", url: "https://www.actionnetwork.com/nfl/real-betting-story", source_name: "Action Network" };
  const report = { updated_at: "2026-10-28", live_newsroom: [news, { headline: "Away at Home", url: "https://www.espn.com/nfl/scoreboard" }] };
  const output = bettingAppReport(report, [{ title: "Away at Home", slug: "2026-10-27-away-at-home", reportDate: "2026-10-27" }]);
  assert.equal(output.live_newsroom[0].url, news.url);
  assert.equal(output.live_newsroom[1].url, "");
  assert.deepEqual(output.sections, []);
});
