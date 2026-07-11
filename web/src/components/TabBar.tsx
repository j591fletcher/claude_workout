export type TabId = "home" | "progress" | "routines" | "coach";

interface Tab {
  id: TabId;
  label: string;
  icon: string;
}

const TABS: Tab[] = [
  { id: "home", label: "Home", icon: "🏠" },
  { id: "progress", label: "Progress", icon: "📈" },
  { id: "routines", label: "Routines", icon: "📋" },
  { id: "coach", label: "Coach", icon: "💬" },
];

interface TabBarProps {
  active: TabId;
  onChange: (tab: TabId) => void;
}

export function TabBar({ active, onChange }: TabBarProps) {
  return (
    <nav className="tab-bar">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          className={`tab-bar__item${tab.id === active ? " tab-bar__item--active" : ""}`}
          onClick={() => onChange(tab.id)}
          aria-current={tab.id === active}
        >
          <span className="tab-bar__icon" aria-hidden="true">{tab.icon}</span>
          <span className="tab-bar__label">{tab.label}</span>
        </button>
      ))}
    </nav>
  );
}
