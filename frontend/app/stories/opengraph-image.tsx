import { ImageResponse } from "next/og";

export const alt = "Match stories — EPL Prediction Lab";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const runtime = "nodejs";

export default async function StoriesOpenGraphImage() {
  // Static — no fetch. A previous version pulled the live story count
  // but Next tries to statically evaluate OG images at build time, and
  // the API isn't running during `npm run build`, so it crashed the
  // build. Share card is evergreen regardless.
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          backgroundColor: "#000",
          color: "#fff",
          padding: 80,
          fontFamily: "Geist, Inter, system-ui, sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span
            style={{
              width: 14,
              height: 14,
              borderRadius: 999,
              backgroundColor: "#E0FF32",
            }}
          />
          <span
            style={{
              fontSize: 28,
              color: "#778899",
              letterSpacing: 2,
              textTransform: "uppercase",
            }}
          >
            predictor.nullshift.sh / stories
          </span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
          <div
            style={{
              fontSize: 108,
              fontWeight: 700,
              lineHeight: 1.05,
              textTransform: "uppercase",
              letterSpacing: "-0.02em",
            }}
          >
            Stories,
            <br />
            match by match.
          </div>
          <div
            style={{
              fontSize: 34,
              color: "#D9D9D9",
              maxWidth: 900,
              lineHeight: 1.35,
            }}
          >
            AI-written narratives for every finished fixture — xG
            reality check, model hit/miss, where the turning point was.
          </div>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: 26,
            color: "#778899",
          }}
        >
          <span style={{ color: "#E0FF32" }}>free · every finished match</span>
          <span>xG · Poisson · Dixon-Coles · Qwen</span>
        </div>
      </div>
    ),
    size,
  );
}
