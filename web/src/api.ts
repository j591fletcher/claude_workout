// Typed client mirroring the pydantic response models in app/contract.py and
// app/hevy/insights.py. Talks only to our own API — see CLAUDE.md §1.

export type Source = "nippard" | "hevy" | "coaching";

export interface Exercise {
  exercise: string;
  sets: number;
  reps: string;
  rpe: string;
  rest: string;
  weight: number | null;
  unit: "lb";
  source: Source;
  notes: string | null;
}

export interface WorkoutFeedItem {
  date: string;
  title: string;
  tracked: boolean;
  description: string | null;
  exercises: Exercise[];
}

export interface ExerciseSummary {
  name: string;
  sessions: number;
  last_done: string;
}

export interface ExerciseHistoryPoint {
  date: string;
  workout_title: string;
  top_weight_lb: number | null;
  sets: number;
  reps: string;
  rpe: string;
  volume_lb: number | null;
}

export interface LastWorkout {
  date: string;
  title: string;
}

export interface DashboardStats {
  total_workouts: number;
  this_week: number;
  last_workout: LastWorkout | null;
  streak_weeks: number;
  recent_prs: Exercise[];
}

export interface RoutineFull {
  title: string;
  exercises: Exercise[];
}

export interface AskRequest {
  question: string;
  program?: string;
  week?: number;
  day?: string;
}

export interface AskResponse {
  answer: string;
  sources: Record<string, unknown>[];
  exercises: Exercise[];
}

export interface ChatRequest {
  message: string;
  program?: string;
  week?: number;
  day?: string;
}

export interface ChatResponse {
  answer: string;
  sources: Record<string, unknown>[];
}

class ApiError extends Error {
  status: number;
  statusText: string;

  constructor(status: number, statusText: string, message?: string) {
    super(message || `${status} ${statusText}`);
    this.status = status;
    this.statusText = statusText;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new ApiError(res.status, res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health"),

  workouts: (limit = 10, offset = 0) =>
    request<WorkoutFeedItem[]>(`/hevy/workouts?limit=${limit}&offset=${offset}`),

  exercises: () => request<ExerciseSummary[]>("/hevy/exercises"),

  exerciseHistory: (name: string) =>
    request<ExerciseHistoryPoint[]>(`/hevy/exercise-history?name=${encodeURIComponent(name)}`),

  stats: () => request<DashboardStats>("/hevy/stats"),

  routinesFull: () => request<RoutineFull[]>("/hevy/routines/full"),

  ask: (body: AskRequest) =>
    request<AskResponse>("/ask", { method: "POST", body: JSON.stringify(body) }),

  chat: (body: ChatRequest) =>
    request<ChatResponse>("/chat", { method: "POST", body: JSON.stringify(body) }),
};

export { ApiError };
