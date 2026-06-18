import { uiClasses } from "../../styles/uiClasses";

interface LoadingIndicatorProps {
  placeholderText: string;
}

export function LoadingIndicator({ placeholderText }: LoadingIndicatorProps): JSX.Element {
  return (
    <div className={uiClasses.loading.shell}>
      <span className={uiClasses.loading.dots} aria-hidden="true">
        <span className={uiClasses.loading.dot} />
        <span className={uiClasses.loading.dot} />
        <span className={uiClasses.loading.dot} />
      </span>
      <span className={uiClasses.loading.placeholder}>{placeholderText}</span>
    </div>
  );
}