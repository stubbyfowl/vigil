import { useState } from "react";
import { post } from "../api/client";
import { Back } from "../components/Shell";
import { Panel } from "../components/Status";
import { useApp } from "../state/app";

type Key = "mood" | "sleep_quality" | "energy" | "stress" | "symptoms";
const SCALES: { key: Key; label: string; low: number; high: number; hint: string }[] = [
  { key: "mood", label: "Mood", low: 1, high: 10, hint: "1 is very low, 10 is great" },
  { key: "sleep_quality", label: "Sleep", low: 1, high: 10, hint: "1 is very poor, 10 is great" },
  { key: "energy", label: "Energy", low: 1, high: 10, hint: "1 is empty, 10 is full" },
  { key: "stress", label: "Stress", low: 1, high: 10, hint: "1 is calm, 10 is extreme" },
  { key: "symptoms", label: "Symptoms", low: 0, high: 5, hint: "0 is none, 5 is severe" },
];

function Scale({ s, value, set }: { s: (typeof SCALES)[number]; value?: number; set: (v: number) => void }) {
  const options = Array.from({ length: s.high - s.low + 1 }, (_, i) => s.low + i);
  return (
    <div className="scale" role="group" aria-label={`${s.label}. ${s.hint}.`}>
      <span className="placard">{s.label}</span>
      <div className="scale-buttons">
        {options.map((n) => <button key={n} className="btn" aria-pressed={value === n} onClick={() => set(n)}>{n}</button>)}
      </div>
    </div>
  );
}

export function CheckIn() {
  const { astronaut, navigate } = useApp();
  const [values, setValues] = useState<Partial<Record<Key, number>>>({});
  const [journal, setJournal] = useState("");
  const [keep, setKeep] = useState(false);
  const [saved, setSaved] = useState<{ journal_score: number; text_kept: boolean; day: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const missing = SCALES.filter((s) => values[s.key] === undefined).map((s) => s.label);

  const submit = async () => {
    setError(null);
    try {
      setSaved(await post("/api/checkin", { astronaut, ...values, journal, keep_text: keep }));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (saved) {
    return (
      <div className="empty" role="status">
        <h2 className="big-title">Check-in saved for day {saved.day}</h2>
        <p>{journal ? `Journal tone score: ${saved.journal_score}.` : "No journal entry today."} {saved.text_kept ? "Your words were kept on this tablet." : "Your words were not stored. Only the score was."}</p>
        <button className="btn primary" style={{ marginTop: 20 }} onClick={() => navigate("/")}>Back to home</button>
      </div>
    );
  }

  return (
    <div className="stack">
      <div className="row"><Back /><h1 className="big-title">Daily check-in</h1></div>
      <div className="split wide-left">
        <Panel title="Tap one number on each line">
          {SCALES.map((s) => <Scale key={s.key} s={s} value={values[s.key]} set={(v) => setValues({ ...values, [s.key]: v })} />)}
        </Panel>
        <div className="stack">
          <Panel title="Journal (optional)">
            <label className="note" htmlFor="journal">Scored on this tablet with a word list. Nothing goes to any cloud.</label>
            <textarea id="journal" className="field" value={journal} maxLength={2000} onChange={(e) => setJournal(e.target.value)} />
            <label className="toggle"><input type="checkbox" checked={keep} onChange={(e) => setKeep(e.target.checked)} /> Keep my words on this tablet</label>
          </Panel>
          <button className="btn primary" disabled={missing.length > 0} onClick={submit}>Save check-in</button>
          {missing.length > 0 && <p className="note">Still needed: {missing.join(", ")}</p>}
          {error && <p role="alert" className="reason">{error}</p>}
        </div>
      </div>
    </div>
  );
}
