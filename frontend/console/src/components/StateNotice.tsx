export function StateNotice({
  title,
  detail,
  tone = "info",
}: {
  title: string;
  detail: string;
  tone?: "error" | "info";
}) {
  const role = tone === "error" ? "alert" : "status";
  const live = tone === "error" ? "assertive" : "polite";

  return (
    <div
      aria-live={live}
      className={`state-notice${tone === "error" ? " state-notice--error" : ""}`}
      role={role}
    >
      <p className="hero-card__eyebrow">{tone === "error" ? "Needs attention" : "Status"}</p>
      <h3>{title}</h3>
      <p>{detail}</p>
    </div>
  );
}
