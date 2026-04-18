// Primary club colors used as subtle identity accents in match cards and
// team headers. Never used as a background for text (contrast would break
// against #fff), only as thin gradient strips / radial-glow behind headlines.
// Neon #E0FF32 stays the single visual hero; these are context colors.
export const TEAM_COLORS: Record<string, string> = {
  arsenal: "#EF0107",
  "aston-villa": "#670E36",
  bournemouth: "#DA291C",
  brentford: "#E30613",
  brighton: "#0057B8",
  burnley: "#6C1D45",
  chelsea: "#034694",
  "crystal-palace": "#1B458F",
  everton: "#003399",
  fulham: "#CC0000",
  ipswich: "#3764A3",
  leeds: "#FFCD00",
  leicester: "#003090",
  liverpool: "#C8102E",
  "manchester-city": "#6CABDD",
  "manchester-united": "#DA291C",
  "newcastle-united": "#241F20",
  "nottingham-forest": "#DD0000",
  southampton: "#D71920",
  sunderland: "#EB172B",
  tottenham: "#132257",
  "west-ham": "#7A263A",
  "wolverhampton-wanderers": "#FDB913",
};

export function colorFor(slug: string, fallback = "#E0FF32"): string {
  return TEAM_COLORS[slug] ?? fallback;
}
