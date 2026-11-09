import type { Series } from "../api/types";
import { SeriesChart } from "../components/Charts";
import { Back } from "../components/Shell";
import { Annunciator, LoadState, Message } from "../components/Status";
import { useData } from "../state/app";

interface Person {
  id: string;
  name: string;
  role: string;
  verdict: "alert" | "normal";
  value: number;
  median: number;
  low: number;
  high: number;
  drift_days: number;
  chart: Series;
}

export function Explainer() {
  const { data, error } = useData<{ available: boolean; day: number; value: number; people: Person[] }>("/api/explainer");
  if (!data) return <><Back /><LoadState error={error} /></>;
  if (!data.available) return <><Back /><Message title="No matching day in this mission.">Try another seed on the Admin screen.</Message></>;
  return (
    <div className="stack">
      <div className="row">
        <Back />
        <h1 className="big-title">Same heart rate. Different meaning.</h1>
      </div>
      <div className="split">
        {data.people.map((p) => (
          <section className="panel person" key={p.id}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <div><h2>{p.name}</h2><p className="note">{p.role}, day {data.day}</p></div>
              {p.verdict === "alert" ? <Annunciator status="red" label="Alert" /> : <Annunciator status="green" label="Normal" />}
            </div>
            <div className="person-value"><b>{p.value}</b><span className="placard">bpm today</span></div>
            <p className="person-range">Normal for {p.name.split(" ")[0]}: <b className="mono">{p.low} to {p.high}</b> bpm</p>
            <SeriesChart series={p.chart} height={230} />
            <p className="alert-message" style={{ fontSize: 21 }}>
              {p.verdict === "alert" ? `${p.value - p.median > 0 ? "+" : ""}${(p.value - p.median).toFixed(1)} bpm above their own normal for ${p.drift_days} days.` : "Right where this person usually is."}
            </p>
          </section>
        ))}
      </div>
      <p className="note">A real day from this simulated mission. One limit for everyone cannot tell these two apart. Vigil can, because it compares each person with themself.</p>
    </div>
  );
}
