import { Construction } from "lucide-react";

interface PlaceholderPageProps {
  title: string;
  description: string;
}

export function PlaceholderPage({
  title,
  description,
}: PlaceholderPageProps) {
  return (
    <section className="placeholder-page">
      <div className="placeholder-icon">
        <Construction size={29} />
      </div>

      <span className="section-label">
        Development milestone
      </span>

      <h2>{title}</h2>
      <p>{description}</p>
    </section>
  );
}