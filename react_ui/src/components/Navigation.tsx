import { uiClasses } from "../styles/uiClasses";

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
    <nav className={uiClasses.navigation.shell}>
      {sections.map((section) => (
        <button
          key={section.id}
          type="button"
          onClick={() => onSelect(section.id)}
          aria-pressed={current === section.id}
          className={[
            uiClasses.navigation.item,
            current === section.id ? uiClasses.navigation.itemActive : uiClasses.navigation.itemInactive
          ].join(" ")}
        >
          {section.label}
        </button>
      ))}
    </nav>
  );
}
