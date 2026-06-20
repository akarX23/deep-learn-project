import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSocketEvent } from "../../hooks/useSocketEvent";
import type { ProgressUpdatePage, StreamProgressUpdateEventBody } from "../../schemas";
import { WebSocketEvents } from "../../schemas";
import { uiClasses } from "../../styles/uiClasses";

interface LoadingIndicatorProps {
  sid: string | null;
  page: ProgressUpdatePage;
  placeholderText: string;
}

const _EXPANDED_LOG_HEIGHT_PX = 144;

function normalizeProgressUpdate(text: string): string {
  const trimmed = text.trim();
  if (!trimmed) {
    return "";
  }
  return trimmed.endsWith(".") ? trimmed.slice(0, -1) : trimmed;
}

export function LoadingIndicator({ sid, page, placeholderText }: LoadingIndicatorProps): JSX.Element {
  const [progressEvents, setProgressEvents] = useState<string[]>([]);
  const [isExpanded, setIsExpanded] = useState(false);
  const viewportRef = useRef<HTMLDivElement | null>(null);

  useSocketEvent<StreamProgressUpdateEventBody>(
    WebSocketEvents.STREAM_PROGRESS_UPDATE_SKT,
    useCallback(
      (payload) => {
        if (!sid || payload.sid !== sid || payload.for_page !== page) {
          return;
        }

        const update = normalizeProgressUpdate(payload.update);
        if (!update) {
          return;
        }

        setProgressEvents((prev) => [...prev, update]);
      },
      [page, sid]
    )
  );

  useEffect(() => {
    if (isExpanded) {
      return;
    }
    if (viewportRef.current) {
      viewportRef.current.scrollTop = viewportRef.current.scrollHeight;
    }
  }, [isExpanded, progressEvents]);

  const currentStatusText = useMemo(() => {
    if (progressEvents.length === 0) {
      return placeholderText;
    }
    return progressEvents[progressEvents.length - 1];
  }, [placeholderText, progressEvents]);

  return (
    <div className={uiClasses.loading.shell} role="status" aria-live="polite">
      <div className={uiClasses.loading.topRow}>
        <button
          type="button"
          className={uiClasses.loading.expandButton}
          onClick={() => setIsExpanded((prev) => !prev)}
          aria-label={isExpanded ? "Collapse progress log" : "Expand progress log"}
          title={isExpanded ? "Collapse progress log" : "Expand progress log"}
        >
          <span
            className={`${uiClasses.loading.expandButtonChevron} ${
              isExpanded ? uiClasses.loading.expandButtonChevronExpanded : ""
            }`}
          >
            &gt;
          </span>
        </button>

        <div className={uiClasses.loading.statusRow}>
          <span className={uiClasses.loading.dots} aria-hidden="true">
            <span className={`${uiClasses.loading.dotBase} ${uiClasses.loading.dotFirst}`} />
            <span className={`${uiClasses.loading.dotBase} ${uiClasses.loading.dotSecond}`} />
            <span className={`${uiClasses.loading.dotBase} ${uiClasses.loading.dotThird}`} />
          </span>
          <span className={uiClasses.loading.placeholder}>{currentStatusText}</span>
        </div>
      </div>

      <div
        className={`${uiClasses.loading.progressContainer} ${
          isExpanded
            ? uiClasses.loading.progressContainerExpanded
            : uiClasses.loading.progressContainerCollapsed
        }`}
        style={{ height: isExpanded ? `${_EXPANDED_LOG_HEIGHT_PX}px` : "0px" }}
      >
        <div ref={viewportRef} className={uiClasses.loading.progressViewport}>
          <div className={uiClasses.loading.progressList}>
            {progressEvents.length === 0 ? (
              <p className={uiClasses.loading.progressItemMuted}>Awaiting progress updates...</p>
            ) : (
              progressEvents.map((item, index) => (
                <p key={`${index}-${item}`} className={uiClasses.loading.progressItem}>
                  {item}
                </p>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}