export default function GsrAppLinks({ source, placement = "header" }: {
  source: string;
  placement?: "header" | "footer";
}) {
  return (
    <aside aria-label="GSR Network Android app" style={{
      background: "#101010", color: "#f5f5f5", borderBlock: "1px solid #383020",
      padding: placement === "header" ? "10px 20px" : "22px 20px",
      fontFamily: "Arial, sans-serif", fontSize: "13px", lineHeight: "1.5",
    }}>
      <div style={{ maxWidth: "1200px", margin: "0 auto", display: "flex", flexWrap: "wrap", gap: "8px 20px", alignItems: "center", justifyContent: "space-between" }}>
        <span><strong>GSR Network</strong><span style={{ color: "#ccc", marginLeft: "10px" }}>Now on Android</span></span>
        <a href={`https://gsrnetwork.io/app?source=${encodeURIComponent(source)}`} style={{ color: "#f2cc65", fontWeight: 700, textDecoration: "underline", textUnderlineOffset: "4px", padding: "4px 0" }}>
          Get the Android app →
        </a>
      </div>
    </aside>
  );
}
