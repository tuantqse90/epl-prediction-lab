import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#000",
          color: "#E0FF32",
          fontSize: 82,
          fontWeight: 800,
          letterSpacing: -3,
          borderRadius: 36,
          fontFamily: "system-ui, sans-serif",
        }}
      >
        EPL
      </div>
    ),
    { ...size },
  );
}
