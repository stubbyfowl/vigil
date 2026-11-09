import { useEffect, useState } from "react";
import { Back } from "../components/Shell";
import { Annunciator, Panel } from "../components/Status";
import { useApp } from "../state/app";

type Phase = "idle" | "waiting" | "vigil";
const THINK_MINUTES = 5;
const VIGIL_STEPS = [
  "Compared today with your own normal",
  "Wrote a plain-language alert",
  "Started the self-care step",
  "Told the Medical Officer",
  "Queued a summary for Earth",
];
const STEP_MS = 280;

const mmss = (minutes: number) => `${String(Math.floor(minutes)).padStart(2, "0")}:${String(Math.floor((minutes % 1) * 60)).padStart(2, "0")}`;

export function DelayTheater() {
  const { live } = useApp();
  const oneWay = live?.delay_minutes ?? 20;
  const secondsPerMinute = live ? live.flight_seconds / live.delay_minutes : 1;
  const [phase, setPhase] = useState<Phase>("idle");
  const [minutes, setMinutes] = useState(0);
  const [steps, setSteps] = useState(0);
  const total = oneWay * 2 + THINK_MINUTES;

  useEffect(() => {
    if (phase === "idle") return;
    const started = Date.now();
    const timer = setInterval(() => {
      const elapsed = Date.now() - started;
      if (phase === "waiting") setMinutes(Math.min(total, elapsed / 1000 / secondsPerMinute));
      else setSteps(Math.min(VIGIL_STEPS.length, Math.floor(elapsed / STEP_MS)));
    }, 80);
    return () => clearInterval(timer);
  }, [phase, total, secondsPerMinute]);

  const start = (next: Phase) => {
    setMinutes(0);
    setSteps(0);
    setPhase(next);
  };

  const outbound = minutes <= oneWay;
  const thinking = minutes > oneWay && minutes <= oneWay + THINK_MINUTES;
  const position = phase !== "waiting" ? 0 : outbound ? (minutes / oneWay) * 100 : thinking ? 100 : 100 - ((minutes - oneWay - THINK_MINUTES) / oneWay) * 100;
  const done = minutes >= total;

  return (
    <div className="stack">
      <div className="row">
        <Back />
        <h1 className="big-title">Delay Theater</h1>
        <span className="spacer" />
        <button className="btn" onClick={() => start("waiting")}>Wait for Earth</button>
        <button className="btn primary" onClick={() => start("vigil")}>Use Vigil</button>
      </div>
      <div className="theater">
        <Panel title="Astronaut">
          {phase === "idle" && <p className="alert-message">Resting heart rate is up. Sleep is down. Is this serious? Choose how to find out.</p>}
          {phase === "waiting" && (
            <>
              <p className="alert-message">{done ? "Reply received. The condition had time to change." : "Waiting for Earth. No guidance yet."}</p>
              <div className="countdown">{mmss(minutes)}</div>
              <p className="note">Time since asking</p>
            </>
          )}
          {phase === "vigil" && (
            <>
              <ul className="vigil-steps">
                {VIGIL_STEPS.map((s, i) => <li key={s} data-on={i < steps}>{i < steps ? "Done" : "..."} <span>{s}</span></li>)}
              </ul>
              {steps === VIGIL_STEPS.length && <Annunciator status="green" label="Acting now, no wait" />}
            </>
          )}
        </Panel>
        <div className="void" aria-hidden="true">
          <span className="placard">{oneWay} min one way</span>
          <div className="void-track"><i style={{ left: `${position}%`, opacity: phase === "waiting" && !thinking && !done ? 1 : 0 }} /></div>
        </div>
        <Panel title="Ground">
          {phase === "idle" && <p className="alert-message">Earth has no idea yet.</p>}
          {phase === "waiting" && <p className="alert-message">{outbound ? "Message in transit." : thinking ? "Flight surgeon reviews the data." : done ? "Reply delivered." : "Reply in transit."}</p>}
          {phase === "vigil" && <p className="alert-message">A summary will arrive in {oneWay} minutes. The astronaut already has a plan.</p>}
        </Panel>
      </div>
      <p className="note">A model of the delay, using the configured {oneWay} minutes one way. {secondsPerMinute < 2 ? `This demo plays ${oneWay} minutes as ${Math.round(oneWay * secondsPerMinute)} seconds.` : ""}</p>
    </div>
  );
}
