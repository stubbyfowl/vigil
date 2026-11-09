import { Back } from "../components/Shell";
import { LoadState, Message, Panel } from "../components/Status";
import { useData } from "../state/app";

interface Stat { mean: number | null; sd: number | null; n: number }
interface Fixed { detected: number; vs_onset: Stat; lead_vigil_earlier: Stat; missed_by_fixed_found_by_vigil: number }
interface Event {
  id: string; title: string; astronaut: string; runs: number; detected: number; unit: string; vigil_vs_onset: Stat;
  fixed?: Record<string, Fixed>; fixed_alarm?: Stat; levels: Record<string, number>;
}
interface Row { l1: Stat; l2: Stat; l3: Stat; fixed_sensitive: Stat; fixed_quiet: Stat }
interface Data { available: boolean; seeds: number[]; events: Event[]; false_alarms: { quiet: Row; non_event: Row } }

function verdict(e: Event): string {
  if (e.id === "solar_storm") return `Vigil passed on the monitor's warning ${Math.abs(e.vigil_vs_onset.mean ?? 0)} hours before onset. A fixed dose alarm fires ${e.fixed_alarm?.mean} hours after onset.`;
  const quiet = e.fixed!.quiet;
  const lead = quiet.lead_vigil_earlier;
  const missed = quiet.missed_by_fixed_found_by_vigil;
  const never = missed > 0 ? ` The fixed alarm never fired in ${missed} of ${e.runs} runs.` : "";
  if (lead.n === 0 || lead.mean === null) return `A fixed alarm never fired.${never}`;
  if (lead.mean >= 1) return `Vigil flagged this ${lead.mean.toFixed(1)} days before the quieter fixed alarm.${never}`;
  return `The quieter fixed alarm was about as fast here, within 1 day.${never}`;
}

function FalseBars({ row }: { row: Row }) {
  const items: [string, number][] = [
    ["Vigil, any alert", row.l1.mean ?? 0],
    ["Vigil, Level 2 or more", row.l2.mean ?? 0],
    ["Fixed limit, quiet", row.fixed_quiet.mean ?? 0],
    ["Fixed limit, sensitive", row.fixed_sensitive.mean ?? 0],
  ];
  const max = Math.max(...items.map(([, v]) => v), 1);
  return (
    <div className="bars">
      {items.map(([label, v]) => (
        <div className="bar-row" key={label}>
          <span>{label}</span>
          <div className="bar-track"><i style={{ width: `${(v / max) * 100}%` }} /></div>
          <b className="mono">{v}</b>
        </div>
      ))}
    </div>
  );
}

export function Results() {
  const { data, error } = useData<Data>("/api/results");
  if (!data) return <><Back /><LoadState error={error} /></>;
  if (!data.available) return <><Back /><Message title="No results yet.">Run: make eval</Message></>;
  return (
    <div className="stack">
      <div className="row">
        <Back />
        <h1 className="big-title">Measured, not claimed</h1>
        <span className="spacer" />
        <span className="placard">{data.seeds.length} simulated missions · Held-out seeds · Simulated data only</span>
      </div>
      <div className="results-grid">
        {data.events.map((e) => (
          <section className="panel" key={e.id}>
            <h2 className="placard">{e.title}</h2>
            <div className="result-num"><b>{e.detected}/{e.runs}</b><span className="note">runs found</span></div>
            <p className="note">{e.id === "solar_storm" ? "Warning comes from the simulated solar monitor." : `First flag ${e.vigil_vs_onset.mean} days after onset (sd ${e.vigil_vs_onset.sd}). This event builds over several days.`}</p>
            <p style={{ marginTop: 8 }}>{verdict(e)}</p>
          </section>
        ))}
      </div>
      <div className="split">
        <Panel title="False alarms per 100 days, quiet control"><FalseBars row={data.false_alarms.quiet} /></Panel>
        <Panel title="False alarms per 100 days, all crew on non-event days"><FalseBars row={data.false_alarms.non_event} /></Panel>
      </div>
      <p className="note">We planted these events ourselves and chose their size, so this shows the method works in simulation. It says nothing about real people. Full table: docs/results.md.</p>
    </div>
  );
}
