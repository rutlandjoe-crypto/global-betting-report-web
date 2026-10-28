import { put } from "@vercel/blob";
import { NextRequest, NextResponse } from "next/server";
import { GET as getReport } from "../report/route";
import { getBettingStories } from "../../lib/betting-editorial";
import { bettingAppReport } from "../../lib/betting-app-report";

export const dynamic = "force-dynamic";

// The Android app already reads this address before its static-file backup.
// Its public read path is separate from the authenticated publication handler.
export async function GET() {
  const response = await getReport();
  const report = await response.json();
  return NextResponse.json(bettingAppReport(report, getBettingStories()), {
    headers: { "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0" },
  });
}

export async function POST(request: NextRequest) {
  try {
    const authHeader = request.headers.get("authorization");
    const expectedToken = process.env.GSR_PUSH_TOKEN;

    if (!expectedToken || authHeader !== `Bearer ${expectedToken}`) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const bodyText = await request.text();

    if (!bodyText) {
      return NextResponse.json({ error: "Empty body" }, { status: 400 });
    }

    const parsed = JSON.parse(bodyText);

    if (!parsed.title || !parsed.updated_at) {
      return NextResponse.json({ error: "Invalid report JSON" }, { status: 400 });
    }

    const blob = await put("reports/latest_report.json", bodyText, {
      access: "public",
      allowOverwrite: true,
      addRandomSuffix: false,
      contentType: "application/json",
    });

    return NextResponse.json({
      ok: true,
      url: blob.url,
      title: parsed.title,
      updated_at: parsed.updated_at,
    });
  } catch (error) {
    console.error("push-report error:", error);
    return NextResponse.json({ error: "Failed to upload report" }, { status: 500 });
  }
}
