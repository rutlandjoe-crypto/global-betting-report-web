import { list } from "@vercel/blob";
import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";
export const revalidate = 0;

type Report = Record<string, unknown>;

function bundledReport(): Report {
  try {
    const file = path.join(process.cwd(), "public", "latest_report.json");
    return JSON.parse(fs.readFileSync(file, "utf8")) as Report;
  } catch {
    return {};
  }
}

function reportTime(report: Report): number {
  return Date.parse(String(report.generated_utc || report.verified_at || ""));
}

export async function GET() {
  const bundled = bundledReport();
  try {
    const { blobs } = await list({
      prefix: "reports/latest_report.json",
      limit: 100,
    });

    const matching = blobs.filter(
      (blob) => blob.pathname === "reports/latest_report.json"
    );

    if (!matching.length) {
      return NextResponse.json(bundled, {
        headers: {
          "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        },
      });
    }

    const latest = [...matching].sort((a, b) => {
      const aTime = new Date(a.uploadedAt ?? 0).getTime();
      const bTime = new Date(b.uploadedAt ?? 0).getTime();
      return bTime - aTime;
    })[0];

    const response = await fetch(latest.url, {
      cache: "no-store",
    });

    if (!response.ok) {
      return NextResponse.json(bundled, {
        headers: {
          "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        },
      });
    }

    const live = (await response.json()) as Report;
    const json =
      !Number.isFinite(reportTime(bundled)) || reportTime(live) >= reportTime(bundled)
        ? live
        : bundled;

    return NextResponse.json(json, {
      headers: {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
      },
    });
  } catch (error) {
    console.error("report route error:", error);
    return NextResponse.json(bundled, {
      headers: {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
      },
    });
  }
}
