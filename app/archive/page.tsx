import type { Metadata } from "next";
import Link from "next/link";
import { getBettingStories } from "@/app/lib/betting-editorial";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Betting Editorial Archive | Global Betting Report",
  description: "Global Betting Report editorial archive.",
  alternates: {
    canonical: "https://www.globalbettingreport.com/archive",
  },
};

export default function ArchivePage() {
  const stories = getBettingStories();

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-5xl px-5 py-10">
        <Link href="/" className="text-sm font-bold text-lime-300 hover:text-white">
          ← Global Betting Report
        </Link>

        <h1 className="mt-6 text-4xl font-black">Editorial Archive</h1>

        <div className="mt-8 space-y-4">
          {stories.map((story) => (
            <article key={story.slug} className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
              <p className="text-xs font-black uppercase tracking-wide text-lime-300">
                {story.label}
              </p>

              <h2 className="mt-2 text-xl font-black">
                <Link href={`/editorial/${story.slug}`} className="hover:text-lime-300">
                  {story.title}
                </Link>
              </h2>

              {story.summary ? (
                <p className="mt-3 text-sm leading-6 text-slate-300">{story.summary}</p>
              ) : null}
            </article>
          ))}
        </div>
      </div>
    </main>
  );
}
