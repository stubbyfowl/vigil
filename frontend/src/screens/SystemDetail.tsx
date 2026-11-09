import type { SystemDetail as Detail } from "../api/types";
import { SeriesChart } from "../components/Charts";
import { Back } from "../components/Shell";
import { Annunciator, LoadState } from "../components/Status";
import { useApp, useData } from "../state/app";

export function SystemDetail({ id }: { id: string }) {
  const { live, astronaut } = useApp();
  const { data, error } = useData<Detail>(live ? `/api/astronaut/${astronaut}/system/${id}?day=${live.day}` : null);
  if (!data) return <><Back /><LoadState error={error} /></>;
  return (
    <div className="stack">
      <div className="row">
        <Back />
        <h1 className="big-title">{data.name}</h1>
        {!data.learning && <Annunciator status={data.status} />}
        <span className="spacer" />
        <span className="placard">Drift {data.score} / 100 · Confidence {Math.round(data.confidence * 100)}%</span>
      </div>
      <p className="note">The shaded band is your own normal. Tap a chart to read any day.</p>
      <div className="tiles">
        {data.signals.map((s) => (
          <section className="panel" key={s.id}>
            <div className="tile-head">
              <div>
                <h3>{s.name}</h3>
                {s.flagged_now ? <span className="drift-tag">Drifting {s.drift_days} d</span> : <span className="note">{s.learning ? "Learning your normal" : "Inside your normal"}</span>}
              </div>
              <div className="tile-value">{s.current === null ? "--" : s.current.toFixed(s.decimals)} <span className="placard">{s.unit}</span></div>
            </div>
            <SeriesChart series={s} height={170} />
          </section>
        ))}
      </div>
    </div>
  );
}
