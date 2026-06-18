import { uiClasses } from "../styles/uiClasses";

interface NavbarProps {
  title: string;
}

export function Navbar({ title }: NavbarProps): JSX.Element {
  return (
    <header className={uiClasses.navbar.shell}>
      <h1 className={uiClasses.navbar.title}>{title}</h1>
      <p className={uiClasses.navbar.subtitle}>AI-powered tutoring with live streamed guidance</p>
    </header>
  );
}