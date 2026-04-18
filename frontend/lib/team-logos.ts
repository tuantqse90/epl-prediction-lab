// EPL crest URLs served by ESPN's public CDN. Keyed by our Understat-derived
// slug. Add new teams here (relegated/promoted sides) as they show up.
export const TEAM_LOGOS: Record<string, string> = {
  arsenal: "https://a.espncdn.com/i/teamlogos/soccer/500/359.png",
  "aston-villa": "https://a.espncdn.com/i/teamlogos/soccer/500/362.png",
  bournemouth: "https://a.espncdn.com/i/teamlogos/soccer/500/349.png",
  brentford: "https://a.espncdn.com/i/teamlogos/soccer/500/337.png",
  brighton: "https://a.espncdn.com/i/teamlogos/soccer/500/331.png",
  burnley: "https://a.espncdn.com/i/teamlogos/soccer/500/379.png",
  chelsea: "https://a.espncdn.com/i/teamlogos/soccer/500/363.png",
  "crystal-palace": "https://a.espncdn.com/i/teamlogos/soccer/500/384.png",
  everton: "https://a.espncdn.com/i/teamlogos/soccer/500/368.png",
  fulham: "https://a.espncdn.com/i/teamlogos/soccer/500/370.png",
  ipswich: "https://a.espncdn.com/i/teamlogos/soccer/500/373.png",
  leeds: "https://a.espncdn.com/i/teamlogos/soccer/500/357.png",
  leicester: "https://a.espncdn.com/i/teamlogos/soccer/500/375.png",
  liverpool: "https://a.espncdn.com/i/teamlogos/soccer/500/364.png",
  "manchester-city": "https://a.espncdn.com/i/teamlogos/soccer/500/382.png",
  "manchester-united": "https://a.espncdn.com/i/teamlogos/soccer/500/360.png",
  "newcastle-united": "https://a.espncdn.com/i/teamlogos/soccer/500/361.png",
  "nottingham-forest": "https://a.espncdn.com/i/teamlogos/soccer/500/393.png",
  southampton: "https://a.espncdn.com/i/teamlogos/soccer/500/376.png",
  sunderland: "https://a.espncdn.com/i/teamlogos/soccer/500/366.png",
  tottenham: "https://a.espncdn.com/i/teamlogos/soccer/500/367.png",
  "west-ham": "https://a.espncdn.com/i/teamlogos/soccer/500/371.png",
  "wolverhampton-wanderers": "https://a.espncdn.com/i/teamlogos/soccer/500/380.png",
};

export function logoFor(slug: string): string | undefined {
  return TEAM_LOGOS[slug];
}
