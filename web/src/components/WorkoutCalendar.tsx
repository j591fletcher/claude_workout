import { useEffect, useMemo, useState } from "react";
import { api, type CalendarDay } from "../api";
import { LoadingSkeleton, ErrorNote } from "./StatusNote";

const MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"];
const WEEKDAY_LABELS = ["M", "T", "W", "T", "F", "S", "S"];

function toDateStr(y: number, m: number, d: number): string {
  return `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

function abbreviate(title: string): string {
  return title.length > 10 ? `${title.slice(0, 9)}…` : title;
}

interface WorkoutCalendarProps {
  onSelectDay: (date: string) => void;
}

export function WorkoutCalendar({ onSelectDay }: WorkoutCalendarProps) {
  const [days, setDays] = useState<CalendarDay[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const today = useMemo(() => new Date(), []);
  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth()); // 0-indexed

  useEffect(() => {
    api.calendar().then(setDays).catch(() => setError("Hevy unreachable"));
  }, []);

  const byDate = useMemo(() => {
    const map = new Map<string, CalendarDay[]>();
    for (const d of days ?? []) {
      const list = map.get(d.date) ?? [];
      list.push(d);
      map.set(d.date, list);
    }
    return map;
  }, [days]);

  if (error) return <ErrorNote message={error} />;
  if (!days) return <LoadingSkeleton lines={5} />;

  const firstOfMonth = new Date(Date.UTC(viewYear, viewMonth, 1));
  const startWeekday = (firstOfMonth.getUTCDay() + 6) % 7; // Mon=0
  const daysInMonth = new Date(Date.UTC(viewYear, viewMonth + 1, 0)).getUTCDate();

  const cells: (number | null)[] = [
    ...Array(startWeekday).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  while (cells.length % 7 !== 0) cells.push(null);

  const todayStr = toDateStr(today.getFullYear(), today.getMonth(), today.getDate());

  function goPrevMonth() {
    if (viewMonth === 0) { setViewYear((y) => y - 1); setViewMonth(11); }
    else setViewMonth((m) => m - 1);
  }
  function goNextMonth() {
    if (viewMonth === 11) { setViewYear((y) => y + 1); setViewMonth(0); }
    else setViewMonth((m) => m + 1);
  }

  return (
    <div className="calendar">
      <div className="calendar__header">
        <button className="calendar__nav" onClick={goPrevMonth} aria-label="Previous month">‹</button>
        <div className="calendar__title">{MONTH_NAMES[viewMonth]} {viewYear}</div>
        <button className="calendar__nav" onClick={goNextMonth} aria-label="Next month">›</button>
      </div>
      <div className="calendar__grid">
        {WEEKDAY_LABELS.map((w, i) => (
          <div key={i} className="calendar__weekday">{w}</div>
        ))}
        {cells.map((day, i) => {
          if (day === null) return <div key={i} className="calendar__cell calendar__cell--empty" />;
          const dateStr = toDateStr(viewYear, viewMonth, day);
          const entries = byDate.get(dateStr) ?? [];
          const hasWorkout = entries.length > 0;
          const isToday = dateStr === todayStr;
          return (
            <button
              key={i}
              className={`calendar__cell${hasWorkout ? " calendar__cell--workout" : ""}${isToday ? " calendar__cell--today" : ""}`}
              onClick={() => hasWorkout && onSelectDay(dateStr)}
              disabled={!hasWorkout}
            >
              <span className="calendar__daynum">{day}</span>
              {hasWorkout && (
                <span className="calendar__labels">
                  <span className="calendar__dot" aria-hidden="true" />
                  {entries.slice(0, 1).map((e) => (
                    <span key={e.title} className="calendar__label">{abbreviate(e.title)}</span>
                  ))}
                  {entries.length > 1 && <span className="calendar__label">+{entries.length - 1}</span>}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
