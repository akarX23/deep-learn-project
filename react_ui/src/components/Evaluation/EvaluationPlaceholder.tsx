import { uiClasses } from "../../styles/uiClasses";

export function EvaluationPlaceholder(): JSX.Element {
  return (
    <section className={uiClasses.placeholder.panel}>
      <h2 className={uiClasses.placeholder.title}>Evaluation</h2>
      <p className={uiClasses.placeholder.text}>Evaluation section is coming soon.</p>
    </section>
  );
}
