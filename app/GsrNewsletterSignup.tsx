"use client";

import { useEffect, useRef } from "react";

export default function GsrNewsletterSignup() {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const host = container.current;
    if (!host || host.querySelector("script[data-beehiiv-form]")) return;
    const script = document.createElement("script");
    script.async = true;
    script.src = "https://subscribe-forms.beehiiv.com/v3/loader.js";
    script.dataset.beehiivForm = "a754116c-9097-4d20-8c8c-78b54ccf59f2";
    host.appendChild(script);
  }, []);

  return (
    <section
      aria-labelledby="gsr-newsletter-heading"
      style={{ margin: "32px auto", padding: "24px 16px", width: "100%", maxWidth: 1000, boxSizing: "border-box", background: "#fff", color: "#111827", borderTop: "2px solid #111827", fontFamily: "Arial, sans-serif" }}
    >
      <h2 id="gsr-newsletter-heading" style={{ margin: "0 0 8px", fontSize: 24, fontWeight: 700, lineHeight: 1.25 }}>
        Get the GSR Network Weekly Roundup
      </h2>
      <p style={{ margin: "0 0 16px", fontSize: 16, lineHeight: 1.6 }}>
        Selected stories from our six newsrooms, plus a note from founder Joe Rutland. Free, once a week.
      </p>
      <div ref={container} style={{ width: "100%", minWidth: 0, overflowWrap: "anywhere" }} />
      <p style={{ margin: "16px 0 0", fontSize: 14, lineHeight: 1.6 }}>
        By subscribing, you agree to receive the weekly roundup and occasional GSR Network news and service offers. Unsubscribe anytime.
      </p>
      <p style={{ margin: "8px 0 0", fontSize: 14, lineHeight: 1.6 }}>
        Form not loading?{" "}
        <a href="https://gsr-network-news.beehiiv.com/subscribe" style={{ color: "#174ea6", textDecoration: "underline" }}>
          Subscribe on beehiiv
        </a>.
      </p>
    </section>
  );
}