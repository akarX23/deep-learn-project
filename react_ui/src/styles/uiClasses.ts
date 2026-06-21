import { theme } from "./theme";

export const uiClasses = {
  layout: {
    page: `min-h-screen bg-gradient-to-br ${theme.pageGradient} ${theme.textPrimary}`,
    container: "mx-auto w-full max-w-6xl px-4 py-6 md:px-8",
    card: `rounded-2xl border ${theme.border} ${theme.surface} p-4 shadow-xl shadow-slate-950/30 md:p-6`
  },
  navbar: {
    shell: `mb-4 rounded-2xl border ${theme.border} ${theme.surface} px-4 py-3 md:mb-6 md:px-6`,
    title: `text-lg font-semibold tracking-wide ${theme.accent} md:text-xl`,
    subtitle: `mt-1 text-xs ${theme.textSoft} md:text-sm`
  },
  navigation: {
    shell: "mb-4 flex flex-wrap gap-2",
    item: "rounded-lg border px-3 py-2 text-sm font-medium transition-colors duration-150",
    itemActive: "border-amber-300/50 bg-amber-300/15 text-amber-200",
    itemInactive: "border-slate-700 bg-slate-900 text-slate-200 hover:bg-slate-800"
  },
  chat: {
    heading: `mt-0 text-xl font-semibold ${theme.accent}`,
    subheading: `mb-4 text-sm ${theme.textMuted}`,
    messages: "mb-4 flex min-h-64 flex-col gap-3",
    bubble: "max-w-[85%] rounded-xl border px-3 py-2",
    userBubble: `self-end border-blue-500/30 ${theme.userBubble} ${theme.textPrimary}`,
    assistantBubble: `self-start ${theme.border} ${theme.assistantBubble} ${theme.textPrimary}`,
    infoBubble: `self-start border-amber-400/30 ${theme.infoBubble} text-amber-100`,
    attachmentChip: "inline-flex items-center rounded-md border border-amber-300/30 bg-amber-300/10 px-2 py-1 text-xs text-amber-100",
    markdownBox: `rounded-lg border ${theme.border} bg-slate-950/60 p-3 leading-relaxed overflow-x-auto \
          [&::-webkit-scrollbar]:h-2 \
          [&::-webkit-scrollbar-track]:bg-slate-800/40 \
          [&::-webkit-scrollbar-thumb]:bg-slate-600 \
          [&::-webkit-scrollbar-thumb]:rounded-md \
          [&::-webkit-scrollbar-button]:hidden`,
    streamRevealBase: "transition-all duration-200 ease-out will-change-transform will-change-opacity",
    streamRevealIdle: "opacity-100 translate-y-0",
    streamRevealActive: "opacity-90 translate-y-0.5",
    errorText: "mt-2 text-sm text-rose-300"
  },
  input: {
    label: "mb-2 block text-sm font-medium text-slate-200",
    textarea: "w-full rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2 text-slate-100 outline-none transition-colors placeholder:text-slate-500 focus:border-amber-300",
    submit: "inline-flex items-center rounded-lg border border-amber-300/40 bg-amber-300/15 px-4 py-2 text-sm font-semibold text-amber-100 transition-colors hover:bg-amber-300/25 disabled:cursor-not-allowed disabled:opacity-50"
  },
  uploader: {
    shell: "mb-4 mt-3",
    row: "flex items-center gap-3",
    picker: "inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-slate-600 bg-slate-800 px-2.5 py-1.5 text-xs font-medium text-slate-100 transition-colors hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50",
    icon: "text-sm",
    helper: "text-sm text-slate-400",
    hiddenInput: "sr-only",
    list: "mt-3 space-y-2",
    fileItem: "flex items-center justify-between rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200",
    remove: "rounded-md border border-rose-400/40 bg-rose-500/10 px-2 py-1 text-xs text-rose-200 transition-colors hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-50",
    errorBox: "mt-2 rounded-lg border border-rose-400/40 bg-rose-500/10 p-2 text-sm text-rose-200"
  },
  loading: {
    shell: "mt-2 rounded-lg border border-slate-700 bg-slate-900/50 p-3 text-sm text-slate-300",
    topRow: "flex items-center gap-2",
    statusRow: "flex items-center gap-2",
    dots: "inline-flex items-center gap-1",
    dotBase: "h-2 w-2 rounded-full bg-amber-300 animate-bounce [animation-duration:700ms] [animation-timing-function:cubic-bezier(0.2,0.8,0.2,1)]",
    dotFirst: "[animation-delay:0ms]",
    dotSecond: "[animation-delay:140ms]",
    dotThird: "[animation-delay:280ms]",
    placeholder: "rounded-md border border-slate-700 bg-slate-900/80 px-2 py-1 text-xs text-slate-200 animate-pulse [animation-duration:1.4s]",
    expandButton: "h-6 w-6 rounded-md border border-slate-600 bg-slate-800/80 text-xs font-semibold text-slate-200 transition-colors hover:bg-slate-700",
    expandButtonChevron: "inline-block transition-transform duration-300 ease-in-out",
    expandButtonChevronExpanded: "rotate-90",
    progressContainer: "overflow-hidden transition-[height,opacity,margin] duration-300 ease-in-out",
    progressContainerExpanded: "mt-3 opacity-100",
    progressContainerCollapsed: "mt-0 opacity-0",
    progressViewport: "h-full overflow-y-auto rounded-md border border-slate-700 bg-slate-950/60 px-2 py-1",
    progressList: "space-y-1",
    progressItem: "text-xs text-slate-300",
    progressItemMuted: "text-xs text-slate-500",
    usage: "mt-2 text-xs text-slate-400"
  },
  placeholder: {
    panel: "rounded-xl border border-slate-700 bg-slate-900/70 p-6",
    title: "mt-0 text-lg font-semibold text-amber-300",
    text: "text-slate-300"
  }
} as const;