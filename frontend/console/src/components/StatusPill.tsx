import { type PropsWithChildren } from "react";

export function StatusPill({
  tone,
  children,
}: PropsWithChildren<{ tone: string }>) {
  const normalized = tone.toLowerCase();
  const className =
    normalized.includes("review")
      ? "status-pill status-pill--review"
      : normalized.includes("blocked") || normalized.includes("failed")
        ? "status-pill status-pill--danger"
        : normalized.includes("accepted") || normalized.includes("healthy")
          ? "status-pill status-pill--good"
          : normalized.includes("input")
            ? "status-pill status-pill--waiting"
            : "status-pill";

  return <span className={className}>{children}</span>;
}
