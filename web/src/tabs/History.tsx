import { useEffect, useRef, useState } from "react";
import { api, type WorkoutFeedItem, ApiError } from "../api";
import { WorkoutCard } from "../components/WorkoutCard";
import { LoadingSkeleton, ErrorNote } from "../components/StatusNote";

const PAGE_SIZE = 10;

interface HistoryProps {
  onSelectExercise: (name: string) => void;
}

export function History({ onSelectExercise }: HistoryProps) {
  const [workouts, setWorkouts] = useState<WorkoutFeedItem[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const loadingRef = useRef(false);

  function loadNextPage() {
    if (loadingRef.current || !hasMore) return;
    loadingRef.current = true;
    setLoading(true);
    api
      .workouts(PAGE_SIZE, offset)
      .then((page) => {
        setWorkouts((prev) => [...prev, ...page]);
        setOffset((prev) => prev + page.length);
        if (page.length < PAGE_SIZE) setHasMore(false);
      })
      .catch((e) => setError(e instanceof ApiError ? "Hevy unreachable" : "Failed to load workouts"))
      .finally(() => {
        loadingRef.current = false;
        setLoading(false);
      });
  }

  useEffect(() => {
    loadNextPage();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) loadNextPage();
    });
    observer.observe(sentinel);
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offset, hasMore]);

  if (error) return <ErrorNote message={error} />;

  return (
    <div className="workout-list">
      {workouts.map((w) => (
        <WorkoutCard key={`${w.date}-${w.title}`} workout={w} onSelectExercise={onSelectExercise} />
      ))}
      {loading && <LoadingSkeleton lines={2} />}
      {!hasMore && workouts.length > 0 && (
        <div style={{ textAlign: "center", color: "var(--text-dim)", fontSize: 13, padding: 8 }}>
          That's everything logged
        </div>
      )}
      <div ref={sentinelRef} />
    </div>
  );
}
