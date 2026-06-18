type Section = "chat" | "quiz" | "evaluation";

interface NavigationProps {
  current: Section;
  onSelect: (section: Section) => void;
}

const sections: { id: Section; label: string }[] = [
  { id: "chat", label: "Chat" },
  { id: "quiz", label: "Quiz" },
  { id: "evaluation", label: "Evaluation" }
];

export function Navigation({ current, onSelect }: NavigationProps): JSX.Element {
  return (
    <nav style={{ display: "flex", gap: 8, marginBottom: 16 }}>
      {sections.map((section) => (
        <button
          key={section.id}
          type="button"
          onClick={() => onSelect(section.id)}
          aria-pressed={current === section.id}
          style={{
            border: "1px solid #d1d5db",
            borderRadius: 8,
            padding: "8px 12px",
            background: current === section.id ? "#111827" : "#ffffff",
            color: current === section.id ? "#ffffff" : "#111827",
            cursor: "pointer"
          }}
        >
          {section.label}
        </button>
      ))}
    </nav>
  );
}
