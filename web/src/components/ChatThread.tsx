import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { api, type Exercise, ApiError } from "../api";
import { SourceBadge } from "./SourceBadge";

type Mode = "coach" | "program";

interface Message {
  role: "user" | "assistant";
  content: string;
  warning: string | null;
  sources?: Record<string, unknown>[];
  exercises?: Exercise[];
}

const STORAGE_KEY = "workout-app.chat-thread";
const GROUNDING_MARKER = "⚠️ Grounding check";

function splitGroundingWarning(text: string): { main: string; warning: string | null } {
  const idx = text.indexOf(GROUNDING_MARKER);
  if (idx === -1) return { main: text, warning: null };
  return { main: text.slice(0, idx).trim(), warning: text.slice(idx).trim() };
}

function loadThread(): Message[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function ChatThread() {
  const [mode, setMode] = useState<Mode>("coach");
  const [messages, setMessages] = useState<Message[]>(loadThread);
  const [input, setInput] = useState("");
  const [program, setProgram] = useState("");
  const [week, setWeek] = useState("");
  const [day, setDay] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text, warning: null }]);
    setLoading(true);

    const filters = {
      program: program.trim() || undefined,
      week: week.trim() ? Number(week) : undefined,
      day: day.trim() || undefined,
    };

    try {
      if (mode === "coach") {
        const res = await api.chat({ message: text, ...filters });
        const { main, warning } = splitGroundingWarning(res.answer);
        setMessages((prev) => [...prev, { role: "assistant", content: main, warning, sources: res.sources }]);
      } else {
        const res = await api.ask({ question: text, ...filters });
        const { main, warning } = splitGroundingWarning(res.answer);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: main, warning, sources: res.sources, exercises: res.exercises },
        ]);
      }
    } catch (e) {
      const content = e instanceof ApiError
        ? "Coach model offline — try again in a moment"
        : "Something went wrong reaching the coach";
      setMessages((prev) => [...prev, { role: "assistant", content, warning: null }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div className="segmented-control">
        <button
          className={`segmented-control__option${mode === "coach" ? " segmented-control__option--active" : ""}`}
          onClick={() => setMode("coach")}
        >
          Coach
        </button>
        <button
          className={`segmented-control__option${mode === "program" ? " segmented-control__option--active" : ""}`}
          onClick={() => setMode("program")}
        >
          Program
        </button>
      </div>

      {mode === "program" && (
        <div className="chat-filters">
          <input placeholder="Program" value={program} onChange={(e) => setProgram(e.target.value)} />
          <input placeholder="Week" value={week} onChange={(e) => setWeek(e.target.value)} />
          <input placeholder="Day" value={day} onChange={(e) => setDay(e.target.value)} />
        </div>
      )}

      <div className="chat-thread">
        {messages.map((m, i) => (
          <div key={i} className={`chat-bubble chat-bubble--${m.role}`}>
            <ReactMarkdown>{m.content}</ReactMarkdown>
            {m.exercises && m.exercises.length > 0 && (
              <div style={{ marginTop: 8 }}>
                {m.exercises.map((ex) => (
                  <div key={ex.exercise} className="exercise-row">
                    <span>
                      <SourceBadge source={ex.source} />
                      {ex.exercise}
                    </span>
                    <span>{ex.sets}x{ex.reps} | RPE {ex.rpe}</span>
                  </div>
                ))}
              </div>
            )}
            {m.warning && <div className="warning-note">{m.warning}</div>}
          </div>
        ))}
        {loading && (
          <div className="chat-bubble chat-bubble--assistant" style={{ color: "var(--text-dim)" }}>
            thinking on the local model…
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-row">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder={mode === "coach" ? "Ask your coach…" : "Ask about your program…"}
        />
        <button onClick={send} disabled={loading}>Send</button>
      </div>
    </div>
  );
}
