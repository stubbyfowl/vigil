import { memo, useEffect, useRef, useState } from "react";
import { post } from "../api/client";
import type { Status, Timeline as Data } from "../api/types";
import { Back } from "../components/Shell";
import { Annunciator, LoadState } from "../components/Status";
import { useApp, useData } from "../state/app";

const CODE_STATUS: Record<string, Status> = { g: "green", y: "yellow", r: "red" };
const THROTTLE_MS = 120;
const RANK: Record<string, number> = { g: 0, y: 1, r: 2 };

function worstByDay(status: Record<string, string>, days: number): string {
  let out = "";
  for (let i = 0; i < days; i++) {
    let worst = "g";
    for (const key in status) if (RANK[status[key][i]] > RANK[worst]) worst = status[key][i];
    out += worst;
  }
  return out;
}

/** One lane of colored runs, drawn once. Scrubbing only moves the cursor. */
const Lane = memo(function Lane({ codes, label }: { codes: string; label: string }) {
  const runs: { start: number; length: number; code: string }[] = [];
  for (let i = 0; i < codes.length; i++) {
    const last = runs[runs.length - 1];
    if (last && last.code === codes[i]) last.length += 1;
    else runs.push({ start: i, length: 1, code: codes[i] });
  }
  const notable = runs.filter((r) => r.code !== "g").length;
  return (
    <svg className="lane" viewBox={`0 0 ${codes.length} 1`} preserveAspectRatio="none" role="img" aria-label={`${label}. ${notable} stretches off nominal.`}>
      {runs.map((r) => <rect key={r.start} x={r.start} width={r.length} y={0} height={1} className={`lane-${r.code}`} />)}
    </svg>
  );
});

export function Timeline() {
  const { live } = useApp();
  const { data, error } = useData<Data>("/api/timeline");
  const [day, setDay] = useState<number | null>(null);
  const lastSent = useRef(0);
  const dragging = useRef(false);

  useEffect(() => {
    if (live && !dragging.current) setDay(live.day);
  }, [live?.day]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!data || day === null) return <><Back /><LoadState error={error} /></>;
  const percent = (d: number) => ((d - 1) / (data.mission_days - 1)) * 100;

  const scrub = (next: number, force = false) => {
    setDay(next);
    const now = Date.now();
    if (force || now - lastSent.current > THROTTLE_MS) {
      lastSent.current = now;
      post("/api/clock", { day: next, running: false });
    }
  };

  return (
    <div className="stack">
      <div className="row">
        <Back />
        <h1 className="big-title">Mission day {day}</h1>
        <span className="spacer" />
        <button className="btn" onClick={() => post("/api/clock", { running: !live?.running })}>{live?.running ? "Pause" : "Play mission"}</button>
      </div>
      <section className="panel">
        <div className="scrub">
          <div className="markers">
            {data.events.map((e) => (
              <button key={e.id} className="marker" style={{ left: `${percent(e.day)}%` }} aria-label={`Jump to ${e.title}, day ${e.day}`} onClick={() => scrub(e.day, true)}>
                <span>{e.title}</span>
              </button>
            ))}
          </div>
          <div className="lanes">
            {data.crew.map((c) => (
              <div className="lane-row" key={c.id}>
                <span className="placard">{c.tag}</span>
                <Lane codes={worstByDay(c.status, data.mission_days)} label={c.name} />
              </div>
            ))}
            <div className="cursor" style={{ left: `calc(56px + (100% - 56px) * ${percent(day) / 100})` }} />
          </div>
          <div className="scrub-input">
            <input
              type="range" min={1} max={data.mission_days} value={day} aria-label="Mission day"
              onPointerDown={() => (dragging.current = true)}
              onPointerUp={(e) => { dragging.current = false; scrub(Number((e.target as HTMLInputElement).value), true); }}
              onChange={(e) => scrub(Number(e.target.value))}
            />
          </div>
        </div>
      </section>
      <section className="panel">
        <table className="status-table">
          <thead>
            <tr><th scope="col">Day {day}</th>{Object.values(data.systems).map((n) => <th key={n} scope="col">{n}</th>)}<th scope="col">Level</th></tr>
          </thead>
          <tbody>
            {data.crew.map((c) => (
              <tr key={c.id}>
                <th scope="row">{c.name}</th>
                {Object.keys(data.systems).map((k) => <td key={k}><Annunciator status={CODE_STATUS[c.status[k][day - 1]]} /></td>)}
                <td className="mono">{c.level[day - 1] || "None"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
