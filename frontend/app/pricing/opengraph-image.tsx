import { ImageResponse } from "next/og";

export const alt = "Pricing — EPL Prediction Lab";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const runtime = "nodejs";

export default async function PricingOpenGraphImage() {
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
            predictor.nullshift.sh / pricing
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 80 }}>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 20,
              flex: 1,
            }}
          >
            <div
              style={{
                fontSize: 28,
                color: "#778899",
                letterSpacing: 2,
                textTransform: "uppercase",
              }}
            >
              Free
            </div>
            <div style={{ fontSize: 180, fontWeight: 700, lineHeight: 1 }}>
              $0
            </div>
            <div style={{ fontSize: 28, color: "#D9D9D9" }}>
              every prediction, forever
            </div>
          </div>

          <div style={{ width: 2, height: 280, backgroundColor: "#333" }} />

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 20,
              flex: 1,
            }}
          >
            <div
              style={{
                fontSize: 28,
                color: "#E0FF32",
                letterSpacing: 2,
                textTransform: "uppercase",
              }}
            >
              Pro
            </div>
            <div
              style={{
                fontSize: 180,
                fontWeight: 700,
                lineHeight: 1,
                color: "#E0FF32",
                display: "flex",
                alignItems: "baseline",
              }}
            >
              $9
              <span style={{ fontSize: 48, color: "#778899", marginLeft: 12 }}>
                /mo
              </span>
            </div>
            <div style={{ fontSize: 28, color: "#D9D9D9" }}>
              10× API · early access · cancel anytime
            </div>
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
          <span>Free. Pro if you want the extras.</span>
          <span>xG doesn't lie. But the bookies do.</span>
        </div>
      </div>
    ),
    size,
  );
}
