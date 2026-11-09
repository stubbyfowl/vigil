import { useEffect, useState } from "react";
import { post } from "../api/client";
import type { Ground as GroundData, Packet, Status } from "../api/types";
import { Back } from "../components/Shell";
import { Annunciator, LoadState } from "../components/Status";
import { routePath, useApp, useData } from "../state/app";

const STATE_WORD = { queued: "Queued", sent: "Sent", in_transit: "In transit", received: "Received" };
const POLL_MS = 400;

function useTick(ms: number): number {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => setTick((t) => t + 1), ms);
    return () => clearInterval(timer);
  }, [ms]);
  return tick;
}

function eta(seconds: number, scale: number): string {
  const total = Math.ceil(seconds * scale);
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

function PacketRow({ p, scale }: { p: Packet; scale: number }) {
  const progress = p.state === "received" ? 100 : p.state === "queued" ? 0 : Math.round((1 - (p.seconds_left ?? 0) / p.flight_seconds) * 100);
  return (
    <li className="packet" data-state={p.state} data-priority={p.priority === 0}>
      <div className="packet-head">
        <span className="packet-title">{p.title}</span>
        <span className="placard">Day {p.mission_day} · {p.size_kb} KB</span>
        <span className="placard packet-state">{STATE_WORD[p.state]}</span>
        <span className="mono packet-eta">{p.state === "in_transit" || p.state === "sent" ? eta(p.seconds_left ?? 0, scale) : p.state === "received" ? "Arrived" : "Waiting"}</span>
      </div>
      <div className="transit"><i style={{ left: `${Math.max(0, Math.min(progress, 100))}%` }} /></div>
    </li>
  );
}

export function Ground() {
  const { live, route } = useApp();
  const tick = useTick(POLL_MS);
  const { data, error } = useData<GroundData>(live ? `/api/ground?day=${live.day}` : null, tick);
  if (!data) return <LoadState error={error} />;
  const scale = (data.delay_minutes * 60) / data.flight_seconds;
  const inFlight = data.packets.filter((p) => p.state === "in_transit" || p.state === "sent");
  const secondWindow = route.includes("pin=1");
  const systems = data.crew[0] ? Object.keys(data.crew[0].systems) : [];
  const cell = (status: Status) => <Annunciator status={status} />;

  return (
    <div className="ground stack">
      <div className="row">
        {!secondWindow && <Back />}
        <h1 className="big-title">Mission control</h1>
        <span className="placard">Earth receives this {data.delay_minutes} minutes late</span>
        <span className="spacer" />
        <button className="btn" onClick={() => post("/api/link", { up: !data.link_up })}>{data.link_up ? "Drop link" : "Restore link"}</button>
        {!secondWindow && routePath(route) === "/ground" && <button className="btn" onClick={() => window.open("/#/ground?pin=1", "vigil-ground")}>Second window</button>}
      </div>
      {data.level3.length > 0 && (
        <section className="level3" role="alert">
          {data.level3.map((a) => (
            <div key={a.id} className="level3-row">
              <Annunciator status="red" label={`${a.astronaut} Level 3`} />
              <b>{a.system}</b>
              <span>{a.reason}</span>
            </div>
          ))}
        </section>
      )}
      <div className="split">
        <section className="panel">
          <h2 className="placard">Crew status · Day {data.day}</h2>
          <table className="status-table">
            <thead>
              <tr><th scope="col">Crew</th>{systems.map((s) => <th key={s} scope="col">{s}</th>)}<th scope="col">radiation</th></tr>
            </thead>
            <tbody>
              {data.crew.map((c) => (
                <tr key={c.id}>
                  <th scope="row">{c.tag}</th>
                  {systems.map((s) => <td key={s}>{cell(c.systems[s])}</td>)}
                  <td>{cell(c.radiation)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="note" style={{ marginTop: 8 }}>Ground sees summaries and Level 3 reasons. Raw values stay on the ship unless the astronaut shares them.</p>
        </section>
        <section className="panel">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <h2 className="placard">Packet timeline</h2>
            <span className="placard">{data.link_up ? `${inFlight.length} in flight` : "Link lost. Packets wait on board."}</span>
          </div>
          {data.packets.length === 0 ? <p className="note">No packets yet. Run the mission to send some.</p> : (
            <ol className="packets">{data.packets.slice(0, 7).map((p) => <PacketRow key={p.id} p={p} scale={scale} />)}</ol>
          )}
          <p className="note">Countdown shows flight time. This demo plays {data.delay_minutes} minutes as {data.flight_seconds} seconds.</p>
        </section>
      </div>
    </div>
  );
}
