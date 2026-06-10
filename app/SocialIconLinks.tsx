const SOCIAL_LINKS = [
  {
    label: "YouTube",
    href: "https://www.youtube.com/@TheGSRNetwork",
    icon: "/images/social/youtube.svg",
  },
  {
    label: "Spotify",
    href: "https://open.spotify.com/show/033twUpbE3ukspgx0T3XNq?si=CilT1aEXRJ2OEFTMdtvF2A",
    icon: "/images/social/spotify.svg",
  },
  {
    label: "TikTok",
    href: "https://www.tiktok.com/@thegsrnetwork",
    icon: "/images/social/tiktok.svg",
  },
  {
    label: "Beehiiv",
    href: "https://gsr-network-news.beehiiv.com/",
    icon: "/images/social/beehiiv.svg",
  },
];

export default function SocialIconLinks({
  hoverClassName = "hover:border-red-400",
}: {
  hoverClassName?: string;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3" aria-label="GSR social links">
      {SOCIAL_LINKS.map((link) => (
        <a
          key={link.label}
          href={link.href}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Follow GSR on ${link.label}`}
          title={link.label}
          className={`inline-flex h-9 w-9 items-center justify-center rounded-full border border-neutral-700 bg-white transition ${hoverClassName}`}
        >
          <img src={link.icon} alt="" className="h-6 w-6" />
        </a>
      ))}
    </div>
  );
}
