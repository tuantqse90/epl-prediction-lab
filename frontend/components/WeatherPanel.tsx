import type { Weather } from "@/lib/api";
import type { Lang } from "@/lib/i18n";

const ICONS: Record<string, string> = {
  clear: "☀️",
  "partly-cloudy": "⛅",
  cloudy: "☁️",
  fog: "🌫",
  drizzle: "🌦",
  rain: "🌧",
  "rain-heavy": "🌧",
  snow: "❄️",
  "snow-heavy": "❄️",
  thunderstorm: "⛈",
};

export default function WeatherPanel({ weather, lang }: { weather: Weather; lang: Lang }) {
  if (!weather || weather.temp_c == null) return null;

  const icon = weather.condition ? ICONS[weather.condition] ?? "" : "";
  const windy = (weather.wind_kmh ?? 0) >= 30;
  const wet = (weather.precip_mm ?? 0) >= 0.5;
  const note: string | null = windy
    ? (lang === "vi" ? "Gió mạnh — khả năng chuyền dài giảm." : "Strong wind — long-ball accuracy drops.")
    : wet
    ? (lang === "vi" ? "Trời ẩm — xử lý bóng có thể khó." : "Wet pitch — touch control is trickier.")
    : null;

  const title = lang === "vi" ? "Thời tiết sân" : "Pitch conditions";

  return (
    <section className="card space-y-2">
      <h2 className="label">{title}</h2>
      <div className="flex items-center gap-4 font-mono text-sm">
        {icon && <span className="text-2xl" aria-hidden>{icon}</span>}
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          <span>
            <span className="stat text-base">{weather.temp_c.toFixed(0)}°C</span>
          </span>
          {weather.wind_kmh != null && (
            <span className={windy ? "text-error" : "text-muted"}>
              {lang === "vi" ? "gió" : "wind"} {weather.wind_kmh.toFixed(0)} km/h
            </span>
          )}
          {weather.precip_mm != null && weather.precip_mm > 0 && (
            <span className={wet ? "text-error" : "text-muted"}>
              {lang === "vi" ? "mưa" : "rain"} {weather.precip_mm.toFixed(1)} mm
            </span>
          )}
        </div>
      </div>
      {note && <p className="text-[11px] text-muted">{note}</p>}
    </section>
  );
}
