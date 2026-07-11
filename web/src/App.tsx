import { useState } from "react";
import { TabBar, type TabId } from "./components/TabBar";
import { Home } from "./tabs/Home";
import { History } from "./tabs/History";
import { Progress } from "./tabs/Progress";
import { Routines } from "./tabs/Routines";
import { Coach } from "./tabs/Coach";

function App() {
  const [tab, setTab] = useState<TabId>("home");
  const [exerciseToShow, setExerciseToShow] = useState<string | null>(null);

  function goToExercise(name: string) {
    setExerciseToShow(name);
    setTab("progress");
  }

  return (
    <div className="app-shell">
      <main className="app-main">
        {tab === "home" && <Home onGoToHistory={() => setTab("history")} />}
        {tab === "history" && <History onSelectExercise={goToExercise} />}
        {tab === "progress" && (
          <Progress preselected={exerciseToShow} onConsumePreselect={() => setExerciseToShow(null)} />
        )}
        {tab === "routines" && <Routines />}
        {tab === "coach" && <Coach />}
      </main>
      <TabBar active={tab} onChange={setTab} />
    </div>
  );
}

export default App;
