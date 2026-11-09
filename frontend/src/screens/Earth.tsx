import { useState } from "react";
import { post } from "../api/client";
import { Back } from "../components/Shell";
import { Annunciator, LevelBadge, LoadState, Panel } from "../components/Status";
import { useApp, useData } from "../state/app";
import type { Status } from "../api/types";
import { ShareToggle } from "./Crew";

interface Decision {
  level: number;
  decision: string;
  title: string;
  detail: string;
  reason: string | null;
  delay_minutes: number;
  preview: { systems: Record<string, Status>; radiation: Status; level3: { id: string; reason: string }[] };
}

export function Earth() {
  const { live, astronaut, navigate } = useApp();
  const { data, error } = useData<Decision>(live ? `/api/astronaut/${astronaut}/earth?day=${live.day}` : null);
  const [note, setNote] = useState("");
  const [sent, setSent] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  if (!data) return <><Back /><LoadState error={error} /></>;

  const send = () =>
    post("/api/call-earth", { astronaut, note })
      .then(() => setSent(true))
      .catch((e: Error) => setSendError(e.message));

  return (
    <div className="stack">
      <div className="row"><Back /><h1 className="big-title">Call Earth</h1><LevelBadge level={data.level} /></div>
      <div className="split">
        <div className="stack">
          <Panel title="Vigil's decision">
            <p className="big-title" style={{ marginBottom: 8 }}>{data.title}</p>
            <p>{data.detail}</p>
            {data.reason && <p className="reason" style={{ marginTop: 8 }}>{data.reason}</p>}
          </Panel>
          <Panel title="One-way delay">
            <p className="delay-number">{data.delay_minutes} min</p>
            <p className="note">Any reply takes at least {data.delay_minutes * 2} minutes. Act on the checklist first.</p>
          </Panel>
        </div>
        <div className="stack">
          <Panel title="What Earth will receive">
            <div className="row">
              {Object.entries(data.preview.systems).map(([k, v]) => <span key={k}><span className="placard">{k} </span><Annunciator status={v} /></span>)}
            </div>
            <p className="note" style={{ marginTop: 8 }}>Status only. No raw values and no journal text.</p>
            <ShareToggle audience="Earth" field="share_ground" />
          </Panel>
          {sent ? (
            <Panel title="Sent">
              <p role="status">Your packet is on its way. It reaches Earth in {data.delay_minutes} minutes.</p>
              <button className="btn" style={{ marginTop: 10 }} onClick={() => navigate("/ground")}>Watch it travel</button>
            </Panel>
          ) : (
            <Panel title="Add a short note (optional)">
              <input aria-label="Note to Earth" className="field" style={{ minHeight: 56 }} maxLength={280} value={note} onChange={(e) => setNote(e.target.value)} />
              <button className="btn primary" style={{ marginTop: 10, width: "100%" }} onClick={send}>{data.level >= 3 ? "Send priority packet" : "Send packet"}</button>
              {sendError && <p role="alert" className="reason">{sendError}</p>}
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}
