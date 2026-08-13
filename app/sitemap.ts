import type { MetadataRoute } from "next";
import {
  getBettingLastModified,
  getBettingStories,
} from "@/app/lib/betting-editorial";

export const dynamic = "force-dynamic";

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = "https://www.globalbettingreport.com";
  const stories = getBettingStories();
  const lastModified = getBettingLastModified();

  return [
    {
      url: baseUrl,
      lastModified,
      changeFrequency: "hourly",
      priority: 1,
    },
    {
      url: `${baseUrl}/archive`,
      lastModified,
      changeFrequency: "hourly",
      priority: 0.8,
    },
    ...stories.map((story) => ({
      url: `${baseUrl}/editorial/${story.slug}`,
      lastModified:
        story.updatedAt && !Number.isNaN(new Date(story.updatedAt).getTime())
          ? new Date(story.updatedAt)
          : lastModified,
      changeFrequency: "daily" as const,
      priority: 0.7,
    })),
  ];
}
