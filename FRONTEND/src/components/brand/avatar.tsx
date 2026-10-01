"use client";

/**
 * Avatars: an uploaded photo, or one of twelve paper-cut illustrations drawn
 * from a student's world (kite, lotus, chai, owl…), or initials.
 */
import { BACKEND_ORIGIN } from "@/core/api";
import { cn } from "@/lib/utils";

type Choice = { id: string; bg: string; fg: string; glyph: React.ReactNode };

const S = { fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" } as const;

export const AVATARS: Choice[] = [
  { id: "kite-blue", bg: "#dfeaf9", fg: "#2f528c", glyph: <g {...S}><path d="M12 3 19 11 12 21 5 11Z" /><path d="M12 3v18M5 11h14" /><path d="M12 21c1 1.5-1 2-.5 3" /></g> },
  { id: "plane-sky", bg: "#f0f5fc", fg: "#3b66ae", glyph: <g {...S}><path d="M3 11 21 4l-9 9-9-2Z" /><path d="M12 13l-1 7 4-5" /></g> },
  { id: "lotus-rose", bg: "#fbe7e2", fg: "#b3574b", glyph: <g {...S}><path d="M12 20c-5 0-8-3-8-6 3 0 6 2 8 6Zm0 0c5 0 8-3 8-6-3 0-6 2-8 6Z" /><path d="M12 20c-2-3-2-9 0-13 2 4 2 10 0 13Z" /></g> },
  { id: "star-marigold", bg: "#fdf0cb", fg: "#a87410", glyph: <g {...S}><path d="m12 3 2.6 5.6 6 .7-4.5 4.1 1.2 6L12 16.5 6.7 19.4l1.2-6L3.4 9.3l6-.7Z" /></g> },
  { id: "owl-sage", bg: "#e3f0e7", fg: "#4a7a5d", glyph: <g {...S}><path d="M6 8c0-3 3-4 6-4s6 1 6 4v6a6 6 0 0 1-12 0Z" /><circle cx="9.5" cy="10" r="1.6" /><circle cx="14.5" cy="10" r="1.6" /><path d="m11 13 1 1 1-1" /></g> },
  { id: "book-ink", bg: "#e7e3d8", fg: "#1e2942", glyph: <g {...S}><path d="M4 5c3-1 6-1 8 1 2-2 5-2 8-1v13c-3-1-6-1-8 1-2-2-5-2-8-1Z" /><path d="M12 6v13" /></g> },
  { id: "sun-marigold", bg: "#fff4d6", fg: "#c48c18", glyph: <g {...S}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></g> },
  { id: "rocket-sky", bg: "#dfeaf9", fg: "#2f528c", glyph: <g {...S}><path d="M12 3c3 2 4 6 3 10l-3 2-3-2c-1-4 0-8 3-10Z" /><circle cx="12" cy="9" r="1.4" /><path d="m9 13-2 3 3-.5M15 13l2 3-3-.5M11 18l1 3 1-3" /></g> },
  { id: "leaf-sage", bg: "#e3f0e7", fg: "#4a7a5d", glyph: <g {...S}><path d="M5 19C5 10 11 5 20 4c0 9-5 15-14 15Z" /><path d="M5 19 14 10" /></g> },
  { id: "moon-ink", bg: "#e7e3d8", fg: "#1e2942", glyph: <g {...S}><path d="M19 15A8 8 0 0 1 9 5a7 7 0 1 0 10 10Z" /><path d="M17 4v2M16 5h2" /></g> },
  { id: "bulb-marigold", bg: "#fdf0cb", fg: "#a87410", glyph: <g {...S}><path d="M9 17h6M10 20h4" /><path d="M12 3a6 6 0 0 0-3.5 10.9c.4.3.5.7.5 1.1v.5h6V15c0-.4.2-.8.5-1.1A6 6 0 0 0 12 3Z" /></g> },
  { id: "chai-amber", bg: "#fbf0d9", fg: "#9a6a1f", glyph: <g {...S}><path d="M5 9h11v5a5 5 0 0 1-5 5h-1a5 5 0 0 1-5-5Z" /><path d="M16 10h1.5a2.5 2.5 0 0 1 0 5H16" /><path d="M8 3c0 1.5 1 1.5 1 3M12 3c0 1.5 1 1.5 1 3" /></g> },
];

export function avatarById(id?: string | null) {
  return AVATARS.find((a) => a.id === id) ?? null;
}

export function Avatar({
  user, size = 40, className,
}: {
  user: { full_name?: string; initials?: string; avatar_url?: string | null; avatar_choice?: string | null; avatar_color?: string } | null;
  size?: number;
  className?: string;
}) {
  const style = { width: size, height: size };
  if (user?.avatar_url) {
    const src = user.avatar_url.startsWith("http") ? user.avatar_url : `${BACKEND_ORIGIN}${user.avatar_url}`;
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt="" style={style} className={cn("rounded-full object-cover ring-2 ring-surface", className)} />;
  }
  const choice = avatarById(user?.avatar_choice);
  if (choice) {
    return (
      <span style={{ ...style, background: choice.bg, color: choice.fg }} className={cn("inline-grid place-items-center rounded-full ring-2 ring-surface", className)}>
        <svg viewBox="0 0 24 24" width={size * 0.58} height={size * 0.58}>{choice.glyph}</svg>
      </span>
    );
  }
  return (
    <span
      style={{ ...style, background: "var(--sky-100)", fontSize: size * 0.38 }}
      className={cn("inline-grid place-items-center rounded-full font-semibold text-sky-700 ring-2 ring-surface", className)}
    >
      {user?.initials || "··"}
    </span>
  );
}

export function AvatarGlyph({ choice, size = 56, selected }: { choice: Choice; size?: number; selected?: boolean }) {
  return (
    <span
      style={{ width: size, height: size, background: choice.bg, color: choice.fg }}
      className={cn("inline-grid place-items-center rounded-full transition-shadow", selected ? "ring-[3px] ring-sky-500 ring-offset-2 ring-offset-surface" : "ring-1 ring-line")}
    >
      <svg viewBox="0 0 24 24" width={size * 0.55} height={size * 0.55}>{choice.glyph}</svg>
    </span>
  );
}
