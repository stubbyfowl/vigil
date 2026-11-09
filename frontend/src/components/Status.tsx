import type { Status } from "../api/types";

export const STATUS_WORD: Record<Status, string> = { green: "Nominal", yellow: "Watch", red: "Act" };

export function StatusIcon({ status }: { status: Status }) {
  const shape =
    status === "green" ? (
      <path d="M2 8.5 6 12.5 14 3.5" fill="none" stroke="currentColor" strokeWidth="2.6" />
    ) : status === "yellow" ? (
      <path d="M8 1.5 15.5 14.5H.5Z" fill="currentColor" />
    ) : (
      <path d="M8 .5 15.5 8 8 15.5.5 8Z" fill="currentColor" />
    );
  return (
    <svg viewBox="0 0 16 16" width="18" height="18" aria-hidden="true">
      {shape}
    </svg>
  );
}

/** A lit legend, like a spacecraft caution panel. Never color alone: always an icon and a word. */
export function Annunciator({ status, label }: { status: Status; label?: string }) {
  return (
    <span className="ann" data-status={status}>
      <StatusIcon status={status} />
      {label ?? STATUS_WORD[status]}
    </span>
  );
}

const LEVEL_STATUS: Record<number, Status> = { 0: "green", 1: "yellow", 2: "yellow", 3: "red" };
const LEVEL_WORD: Record<number, string> = {
  0: "Clear",
  1: "Level 1 · Self-care",
  2: "Level 2 · Tell Medical Officer",
  3: "Level 3 · Call Earth",
};

export function LevelBadge({ level }: { level: number }) {
  return <Annunciator status={LEVEL_STATUS[level]} label={LEVEL_WORD[level]} />;
}

export function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="panel">
      <h2 className="placard">{title}</h2>
      {children}
    </section>
  );
}

export function Message({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="empty" role="status">
      <h2>{title}</h2>
      {children && <p>{children}</p>}
    </div>
  );
}

export function LoadState({ error }: { error: string | null }) {
  return error ? <Message title="This screen could not load.">{error}</Message> : <Message title="Loading" />;
}
