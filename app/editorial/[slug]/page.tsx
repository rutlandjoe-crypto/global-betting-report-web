import type { Metadata } from "next";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";
import { getBettingStory } from "@/app/lib/betting-editorial";

export const dynamic = "force-dynamic";

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const story = getBettingStory(slug);

  if (!story) return {};

  return {
    title: `${story.title} | Global Betting Report`,
    description: story.summary || story.title,
    alternates: {
      canonical: `https://www.globalbettingreport.com/editorial/${story.slug}`,
    },
  };
}

function Section({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
      <h2 className="text-sm font-black uppercase tracking-wide text-lime-300">
        {title}
      </h2>
      <div className="mt-3 space-y-2">
        {items.map((item, index) => (
          <p key={index} className="text-sm leading-6 text-slate-200">
            {item}
          </p>
        ))}
      </div>
    </section>
  );
}

export default async function EditorialPage({ params }: Props) {
  const { slug } = await params;
  const story = getBettingStory(slug);

  if (!story) notFound();
  if (slug !== story.slug) permanentRedirect(`/editorial/${story.slug}`);

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <article className="mx-auto max-w-5xl px-5 py-10">
        <div className="flex gap-4 text-sm font-bold">
          <Link href="/" className="text-lime-300 hover:text-white">
            ← Global Betting Report
          </Link>
          <Link href="/archive" className="text-lime-300 hover:text-white">
            Editorial Archive
          </Link>
        </div>

        <p className="mt-8 text-xs font-black uppercase tracking-wide text-lime-300">
          {story.label}
        </p>

        <h1 className="mt-3 text-4xl font-black leading-tight">
          {story.title}
        </h1>

        {story.updatedAt ? (
          <p className="mt-3 text-sm text-slate-400">
            Updated: {story.updatedAt}
          </p>
        ) : null}

        {story.summary ? (
          <p className="mt-6 text-lg leading-8 text-slate-200">
            {story.summary}
          </p>
        ) : null}

        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <Section title="Game" items={[story.game]} />
          <Section title="Market / Key Data" items={story.market} />
          <Section title="Implied Probability" items={story.impliedProbability} />
          <Section title="Why It Matters" items={story.whyItMatters} />
          <Section title="What To Watch" items={story.whatToWatch} />
          <Section title="Story Angles" items={story.storyAngles} />
        </div>

        {story.sourceUrl ? (
          <section className="mt-8">
            <a
              href={story.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="font-bold text-lime-300 underline"
            >
              Read original source
            </a>
          </section>
        ) : null}
      </article>
    </main>
  );
}
