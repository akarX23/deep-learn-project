import { uiClasses } from "../../styles/uiClasses";

export function QuizPlaceholder(): JSX.Element {
  return (
    <section className={uiClasses.placeholder.panel}>
      <h2 className={uiClasses.placeholder.title}>Quiz</h2>
      <p className={uiClasses.placeholder.text}>Quiz section is coming soon.</p>
    </section>
  );
}
