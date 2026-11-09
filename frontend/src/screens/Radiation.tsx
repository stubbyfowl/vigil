import { useEffect, useState } from "react";
import type { Radiation as Rad, Storm } from "../api/types";
import { Back } from "../components/Shell";
import { Annunciator, LoadState, Panel } from "../components/Status";
import { useApp, useData } from "../state/app";

const SHELTER_STEPS = [
  "Stop your task. Secure loose items.",
  "Put on your personal dosimeter.",
  "Go to the storm shelter.",
  "Close the hatch. Confirm all crew are inside.",
  "Stay until Vigil shows the all clear.",
];
const WARNING_SECONDS = 2 * 60 * 60;

function clock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const parts = [Math.floor(s / 3600), Math.floor((s % 3600) / 60), s % 60];
  return parts.map((p) => String(p).padStart(2, "0")).join(":");
}

export function ShelterFlow({ drill, storm }: { drill: boolean; storm?: Storm }) {
  const { live } = useApp();
  const scale = live ? (live.delay_minutes * 60) / live.flight_seconds : 60;
  const [done, setDone] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const started = Date.now();
    const timer = setInterval(() => setElapsed(((Date.now() - started) / 1000) * scale), 250);
    return () => clearInterval(timer);
  }, [scale]);

  const finished = done === SHELTER_STEPS.length;
  const left = WARNING_SECONDS - elapsed;
  return (
    <div className="shelter" data-pulse={!finished}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <Annunciator status="red" label={drill ? "Drill · Shelter now" : "Shelter now"} />
        <div>
          <span className="placard">{left > 0 ? "Spike expected in" : "Storm is here"}</span>
          <div className="countdown">{clock(left)}</div>
        </div>
      </div>
      <ol className="steps">
        {SHELTER_STEPS.map((step, i) => (
          <li key={step}>
            <button className="step" disabled={i !== done} data-done={i < done} onClick={() => setDone(i + 1)}>
              <span className="mono">{i < done ? "DONE" : i + 1}</span>
              {step}
            </button>
          </li>
        ))}
      </ol>
      {finished && (
        <p role="status">
          {drill ? "Drill complete. All steps done." : "You are in the shelter."}
          {storm?.shelter_dose_msv !== undefined && ` Dose logged in shelter so far: ${storm.shelter_dose_msv} mSv. With no shelter: ${storm.unsheltered_dose_msv} mSv.`}
        </p>
      )}
    </div>
  );
}

function DoseBar({ r }: { r: Rad }) {
  const pct = (v: number) => `${Math.min((v / r.limit_msv) * 100, 100)}%`;
  return (
    <div>
      <div className="dose-track" role="img" aria-label={`Career dose ${r.career_dose_msv} of ${r.limit_msv} millisieverts. Projected ${r.projected_total_msv}.`}>
        <i className="dose-projected" style={{ width: pct(r.projected_total_msv) }} />
        <i className="dose-now" style={{ width: pct(r.career_dose_msv) }} />
        <i className="dose-prior" style={{ width: pct(r.prior_dose_msv) }} />
      </div>
      <div className="dose-legend">
        <span>Before this mission {r.prior_dose_msv}</span>
        <span>This mission {r.mission_dose_msv}</span>
        <span>Projected {r.projected_total_msv}</span>
        <span>Limit {r.limit_msv} mSv</span>
      </div>
    </div>
  );
}

const Stat = ({ label, value, unit }: { label: string; value: string | number; unit: string }) => (
  <div className="stat">
    <span className="placard">{label}</span>
    <b>{value}</b>
    <span className="note">{unit}</span>
  </div>
);

function StormTrace({ storm }: { storm: Storm }) {
  if (!storm.hourly || !storm.hourly_free) return null;
  const w = 560;
  const h = 130;
  const max = Math.max(...storm.hourly_free);
  const path = (data: number[]) => data.map((v, i) => `${i ? "L" : "M"}${(i / (data.length - 1)) * w} ${h - 18 - (v / max) * (h - 26)}`).join("");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Dose rate by hour during the storm, with and without the shelter." style={{ width: "100%" }}>
      <path d={path(storm.hourly_free)} className="median" />
      <path d={path(storm.hourly)} className="trace" />
      <text x={0} y={h - 2} className="tick">Solid: your dosimeter. Dotted: no shelter.</text>
    </svg>
  );
}

export function Radiation() {
  const { live, astronaut } = useApp();
  const [drill, setDrill] = useState(false);
  const { data, error } = useData<Rad>(live ? `/api/astronaut/${astronaut}/radiation?day=${live.day}` : null);
  if (!data) return <><Back /><LoadState error={error} /></>;
  const active = data.storm.phase === "active";
  return (
    <div className="stack">
      <div className="row">
        <Back />
        <h1 className="big-title">Radiation</h1>
        <Annunciator status={data.status} />
        <span className="spacer" />
        {!active && <button className="btn" onClick={() => setDrill(!drill)}>{drill ? "End drill" : "Storm drill"}</button>}
      </div>
      <Panel title="Career dose against the limit"><DoseBar r={data} /></Panel>
      <div className="split">
        <div className="stack">
          <div className="stats">
            <Stat label="Today" value={data.today_dose_msv} unit="mSv" />
            <Stat label="Dose rate" value={data.dose_rate_usv_h} unit="uSv per hour" />
            <Stat label="Projected at end" value={data.projected_total_msv} unit="mSv career total" />
          </div>
          <Panel title="Storm status">
            {active ? <p className="alert-message">Solar storm in progress.</p> : data.storm.phase === "passed" ? <p>Last storm has passed. Dose in shelter: {data.storm.shelter_dose_msv} mSv. With no shelter: {data.storm.unsheltered_dose_msv} mSv.</p> : <p>No storm flag from the solar monitor.</p>}
            {data.storm.phase !== "none" && <StormTrace storm={data.storm} />}
          </Panel>
          <p className="note">Limit and dose figures are approximate and marked must verify. The storm size and shelter factor are invented for this simulation.</p>
        </div>
        <div className="stack">
          {active ? <Panel title="Shelter steps"><ShelterFlow drill={false} storm={data.storm} /></Panel> : drill ? <Panel title="Storm drill"><ShelterFlow drill /></Panel> : <Panel title="Practice"><p>Run a storm drill to rehearse the shelter steps with a timer.</p></Panel>}
        </div>
      </div>
    </div>
  );
}
