import { useState } from "react";
import { post } from "../api/client";
import type { Alert, AlertDetail as Detail } from "../api/types";
import { SeriesChart } from "../components/Charts";
import { Back } from "../components/Shell";
import { LevelBadge, LoadState, Panel } from "../components/Status";
import { useApp, useData } from "../state/app";

function WhyDrawer({ alert, close }: { alert: Alert; close: () => void }) {
  return (
    <aside className="drawer" aria-label="Why this alert fired">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2 className="big-title">Why?</h2>
        <button className="btn" onClick={close}>Close</button>
      </div>
      <p className="reason" style={{ margin: "10px 0" }}>{alert.level_reason}</p>
      {alert.why.signals.map((s) => (
        <div className="why-row" key={s.signal}>
          <h3>{s.name}</h3>
          <div className="why-grid">
            <div><span className="placard">Your normal</span><b>{s.baseline_low} to {s.baseline_high}</b></div>
            <div><span className="placard">Now</span><b>{s.current} {s.unit}</b></div>
            <div><span className="placard">Change</span><b>{s.change > 0 ? "+" : ""}{s.change}</b></div>
            <div><span className="placard">Days</span><b>{s.days_of_drift}</b></div>
          </div>
          <p className="note">{s.rule}</p>
        </div>
      ))}
      <p className="note" style={{ marginTop: 12 }}>{alert.disclaimer} Thresholds are starting values, not clinical limits.</p>
    </aside>
  );
}

export function AlertDetail({ id }: { id: string }) {
  const { live, astronaut, navigate } = useApp();
  const [why, setWhy] = useState(false);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const owner = id.split("-")[0] || astronaut;
  const { data, error, reload } = useData<Detail>(live ? `/api/astronaut/${owner}/alert/${id}?day=${live.day}` : null);

  if (!data) return <><Back /><LoadState error={error} /></>;
  const { alert, charts, protocol, protocol_label: label } = data;

  const act = async (action: "done" | "snooze" | "escalate") => {
    setBusy(true);
    setActionError(null);
    try {
      await post(`/api/astronaut/${owner}/alert/${id}/action`, { action });
      if (action === "escalate") reload();
      else navigate("/");
    } catch (e) {
      setActionError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="stack">
      <div className="row">
        <Back />
        <LevelBadge level={alert.level} />
        <h1 className="placard" style={{ fontSize: 24 }}>{alert.system_name}</h1>
        {data.closed && <span className="placard">This alert has closed</span>}
        {alert.recovering && <span className="placard">Readings are recovering</span>}
        <span className="spacer" />
        <button className="btn" onClick={() => setWhy(true)}>Why?</button>
      </div>
      <div className="split">
        <div className="stack">
          <Panel title="What Vigil sees"><p className="alert-message">{alert.message}</p></Panel>
          <Panel title="Do this">
            <p className="do-this">{alert.action}</p>
            <p className="reason" style={{ marginTop: 6 }}>{alert.recheck_text}</p>
          </Panel>
          <div className="row">
            <button className="btn primary grow" disabled={busy} onClick={() => act("done")}>Done</button>
            <button className="btn grow" disabled={busy} onClick={() => act("snooze")}>Snooze 2 hours</button>
            <button className="btn danger grow" disabled={busy || alert.level >= 3} onClick={() => act("escalate")}>Escalate</button>
          </div>
          {actionError && <p role="alert" className="reason">{actionError}</p>}
          <p className="reason">{alert.level_reason}</p>
          <p className="note">{alert.disclaimer}</p>
          {protocol && (
            <Panel title={`${protocol.name} · ${protocol.minutes} min`}>
              <p>{protocol.steps.join(" ")}</p>
              <p className="note" style={{ marginTop: 6 }}>Stop and escalate if: {protocol.escalate_if} {label}</p>
            </Panel>
          )}
        </div>
        <div className="stack">
          {charts.map((c, i) => (
            <Panel key={c.id} title={c.name}>
              <SeriesChart series={c} height={i === 0 ? 240 : 150} />
            </Panel>
          ))}
          {charts.length === 0 && <Panel title="Dose rate"><p>Open Radiation for the storm view.</p></Panel>}
        </div>
      </div>
      {why && <WhyDrawer alert={alert} close={() => setWhy(false)} />}
    </div>
  );
}
