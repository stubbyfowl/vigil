import { post } from "../api/client";
import type { CrewCard } from "../api/types";
import { Sparkline } from "../components/Charts";
import { Back } from "../components/Shell";
import { Annunciator, LevelBadge, LoadState } from "../components/Status";
import { useApp, useData } from "../state/app";

export function ShareToggle({ audience, field }: { audience: string; field: "share_crew" | "share_ground" }) {
  const { astronaut } = useApp();
  const { data, reload } = useData<Record<string, boolean>>(`/api/astronaut/${astronaut}/share`);
  const on = data?.[field] ?? false;
  const flip = () => post(`/api/astronaut/${astronaut}/share`, { [field]: !on }).then(reload);
  return (
    <label className="toggle">
      <input type="checkbox" checked={on} onChange={flip} /> Share my raw values with {audience}
    </label>
  );
}

export function Crew() {
  const { live } = useApp();
  const { data, error } = useData<{ crew: CrewCard[]; summary: string }>(live ? `/api/crew-view?day=${live.day}` : null);
  if (!data) return <><Back /><LoadState error={error} /></>;
  return (
    <div className="stack">
      <div className="row">
        <Back />
        <h1 className="big-title">Crew</h1>
        <span className="spacer" />
        <span className="alert-message">{data.summary}</span>
      </div>
      <div className="crew-table">
        {data.crew.map((m) => (
          <section key={m.id} className="panel crew-row">
            <div className="crew-name">
              <h2>{m.name}</h2>
              <p className="note">{m.role}</p>
              {m.max_level > 0 && <LevelBadge level={m.max_level} />}
            </div>
            {m.systems.map((s) => (
              <div key={s.id} className="crew-cell">
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <span className="placard">{s.name}</span>
                </div>
                {s.learning ? <span className="note">Learning</span> : <Annunciator status={s.status} />}
                <Sparkline values={s.trend} label={`${m.name} ${s.name}`} height={44} />
              </div>
            ))}
          </section>
        ))}
      </div>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <p className="note">The crew sees trends and status only. Raw values and journal text stay private.</p>
        <ShareToggle audience="the crew" field="share_crew" />
      </div>
    </div>
  );
}
