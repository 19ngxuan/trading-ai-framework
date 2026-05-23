type EmptyStateProps = {
  title: string;
  detail?: string;
};

export function EmptyState({ title, detail }: EmptyStateProps) {
  return (
    <div className="state-box">
      <strong>{title}</strong>
      {detail && <p>{detail}</p>}
    </div>
  );
}
