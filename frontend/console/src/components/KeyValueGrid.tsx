export function KeyValueGrid({
  values,
}: {
  values: Array<{ label: string; value: string | number | null | undefined }>;
}) {
  return (
    <dl className="key-value-grid">
      {values.map((item) => (
        <div className="key-value-grid__row" key={item.label}>
          <dt>{item.label}</dt>
          <dd>{item.value ?? "—"}</dd>
        </div>
      ))}
    </dl>
  );
}
