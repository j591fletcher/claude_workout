export function LoadingSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="skeleton" aria-busy="true" aria-label="Loading">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="skeleton__line" />
      ))}
    </div>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return <div className="error-note">{message}</div>;
}
