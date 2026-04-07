export function StateNotice({
  title,
  detail,
  tone = "info",
}: {
  title: string;
  detail: string;
  tone?: "error" | "info";
}) {
  return (
    <div className={`state-notice${tone === "error" ? " state-notice--error" : ""}`}>
      <p className="hero-card__eyebrow">{tone === "error" ? "Needs attention" : "Status"}</p>
      <h3>{title}</h3>
      <p>{detail}</p>
    </div>
  );
}
