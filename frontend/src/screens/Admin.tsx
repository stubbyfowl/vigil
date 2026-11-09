import { useEffect, useState } from "react";
import { post, put } from "../api/client";
import { Back } from "../components/Shell";
import { LoadState, Panel } from "../components/Status";
import { useData } from "../state/app";

type Group = Record<string, unknown>;
type Config = Record<string, unknown> & { disabled_signals: string[] };
const GROUPS = ["mission", "sync", "detector", "baseline", "escalation", "status", "radiation"];

export function Admin() {
  const { data, error, reload } = useData<{ config: Config; signals: { id: string; name: string }[] }>("/api/admin/config");
  const [draft, setDraft] = useState<Config | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => { if (data) setDraft(data.config); }, [data]);
  if (!data || !draft) return <><Back /><LoadState error={error} /></>;

  const change = (group: string, key: string, value: unknown) => setDraft({ ...draft, [group]: { ...(draft[group] as Group), [key]: value } });
  const toggleSignal = (id: string) => {
    const off = draft.disabled_signals;
    setDraft({ ...draft, disabled_signals: off.includes(id) ? off.filter((s) => s !== id) : [...off, id] });
  };
  const values = () => Object.fromEntries([...GROUPS, "disabled_signals"].map((g) => [g, draft[g]]));
  const save = () => put("/api/admin/config", { values: values() }).then(() => setMessage("Saved. The mission was recomputed.")).catch((e: Error) => setMessage(e.message));
  const restore = () => post("/api/admin/reset").then(() => { setMessage("Defaults restored."); reload(); }).catch((e: Error) => setMessage(e.message));

  return (
    <div className="stack">
      <div className="row">
        <Back />
        <h1 className="big-title">Admin</h1>
        <span className="placard">Starting values, not clinical limits</span>
        <span className="spacer" />
        <button className="btn" onClick={restore}>Restore defaults</button>
        <button className="btn primary" onClick={save}>Save</button>
      </div>
      {message && <p role="status">{message}</p>}
      <div className="admin-grid">
        {GROUPS.map((g) => (
          <Panel key={g} title={g}>
            {Object.entries(draft[g] as Group).map(([k, v]) => (
              <label className="admin-field" key={k}>
                <span>{k.replaceAll("_", " ")}</span>
                {typeof v === "number" ? (
                  <input type="number" step="any" min={0} value={v} onChange={(e) => change(g, k, e.target.value === "" ? 0 : Number(e.target.value))} />
                ) : typeof v === "boolean" ? (
                  <input type="checkbox" checked={v} onChange={(e) => change(g, k, e.target.checked)} />
                ) : (
                  <input value={String(v)} onChange={(e) => change(g, k, e.target.value)} />
                )}
              </label>
            ))}
          </Panel>
        ))}
        <Panel title="Signals on or off">
          {data.signals.map((s) => (
            <label className="admin-field" key={s.id}>
              <span>{s.name}</span>
              <input type="checkbox" checked={!draft.disabled_signals.includes(s.id)} onChange={() => toggleSignal(s.id)} />
            </label>
          ))}
        </Panel>
      </div>
    </div>
  );
}
