import type { LucideIcon } from "lucide-react";

interface Props {
  title: string;
  icon: LucideIcon;
  phase: string;
  summary: string;
}

/** Hali qurilmagan ekran: nima bo'lishini va qaysi bosqichda kelishini aytadi. */
export function PlaceholderScreen({ title, icon: Icon, phase, summary }: Props) {
  return (
    <section className="empty">
      <Icon size={40} strokeWidth={1.25} />
      <h2>{title}</h2>
      <p>{summary}</p>
      <div className="phase">
        <span className="pill ask">{phase} bosqichida</span>
      </div>
    </section>
  );
}
