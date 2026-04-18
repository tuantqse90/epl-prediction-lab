import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "EPL Prediction Lab",
    short_name: "EPL Lab",
    description:
      "xG-driven Poisson + Dixon-Coles predictions, value bets, and reasoning for every Premier League match.",
    start_url: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#000000",
    theme_color: "#000000",
    lang: "vi",
    categories: ["sports", "utilities"],
    icons: [
      { src: "/icon", sizes: "512x512", type: "image/png" },
      { src: "/apple-icon", sizes: "180x180", type: "image/png" },
    ],
  };
}
