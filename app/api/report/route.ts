import { list } from "@vercel/blob";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET() {
  try {
    const { blobs } = await list({
      prefix: "reports/latest_report.json",
      limit: 100,
    });

    const matching = blobs.filter(
      (blob) => blob.pathname === "reports/latest_report.json"
    );

    if (!matching.length) {
      return NextResponse.json(
        { error: "Live report not found" },
        {
          status: 404,
          headers: {
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
          },
        }
      );
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
      return NextResponse.json(
        { error: "Could not fetch live report" },
        {
          status: 502,
          headers: {
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
          },
        }
      );
    }

    const json = await response.json();

    return NextResponse.json(json, {
      headers: {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
      },
    });
  } catch (error) {
    console.error("report route error:", error);
    return NextResponse.json(
      { error: "Failed to load live report" },
      {
        status: 500,
        headers: {
          "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        },
      }
    );
  }
}