import fs from "fs";
import path from "path";

export default function SampleReport() {
  const reportPath = path.join(
    process.cwd(),
    "..",
    "sports_bot-ai",
    "global_sports_report.txt"
  );

  let report = "No report found yet. Run your Python generator first.";

  try {
    report = fs.readFileSync(reportPath, "utf8");
  } catch {
    report = "No report found yet. Run your Python generator first.";
  }

  return (
    <main
      style={{
        fontFamily: "Arial, sans-serif",
        background: "#f9fafb",
        minHeight: "100vh",
        margin: 0,
      }}
    >
      <div
        style={{
          background: "#111827",
          color: "white",
          padding: "20px 40px",
          fontSize: "24px",
          fontWeight: "bold",
        }}
      >
        Global Sports Report
      </div>

      <div
        style={{
          maxWidth: "900px",
          margin: "40px auto",
          padding: "0 20px",
        }}
      >
        <h1
          style={{
            fontSize: "32px",
            marginBottom: "10px",
          }}
        >
          Daily Report
        </h1>

        <p
          style={{
            color: "#6b7280",
            marginBottom: "25px",
          }}
        >
          Automated cross-league snapshot built to support journalists and
          analysts.
        </p>

        <div
          style={{
            background: "white",
            padding: "25px",
            borderRadius: "12px",
            boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
          }}
        >
          <pre
            style={{
              whiteSpace: "pre-wrap",
              lineHeight: "1.6",
              fontSize: "15px",
              margin: 0,
            }}
          >
            {report}
          </pre>
        </div>
      </div>
    </main>
  );
}