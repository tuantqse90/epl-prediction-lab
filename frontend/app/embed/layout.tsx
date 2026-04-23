// Embed routes render without the site header/footer so the partner
// blog pasting the iframe gets just the card, not the whole chrome.
// Keeps the same globals.css (design tokens) from the root layout.

export const metadata = {
  robots: { index: false, follow: false },
};

export default function EmbedLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
