import { type PropsWithChildren } from "react";

export function Panel({
  title,
  eyebrow,
  children,
}: PropsWithChildren<{ title: string; eyebrow?: string }>) {
  return (
    <section className="panel">
      <header className="panel__header">
        {eyebrow ? <p className="panel__eyebrow">{eyebrow}</p> : null}
        <h2>{title}</h2>
      </header>
      {children}
    </section>
  );
}
