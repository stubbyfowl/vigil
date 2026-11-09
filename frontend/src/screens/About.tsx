import { Back } from "../components/Shell";
import { LoadState, Panel } from "../components/Status";
import { useData } from "../state/app";

interface Data {
  statement: string;
  must_verify_count: number;
  sources: { name: string; use: string; status: string }[];
}

export function About() {
  const { data, error } = useData<Data>("/api/about");
  if (!data) return <><Back /><LoadState error={error} /></>;
  return (
    <div className="stack">
      <div className="row"><Back /><h1 className="big-title">About and honesty</h1></div>
      <Panel title="Data honesty"><p className="alert-message">{data.statement}</p></Panel>
      <div className="split">
        <Panel title="What this is">
          <p>Vigil is a student prototype for the NASA Space Apps Challenge. No flight surgeon has reviewed it. The crew are invented. Protocols are samples, not medical advice.</p>
          <p className="note" style={{ marginTop: 8 }}>{data.must_verify_count} reference figures are still marked "must verify". See data/real_ranges.json and SOURCES.md.</p>
        </Panel>
        <Panel title="Fonts and privacy">
          <p>Vigil makes no network calls outside this machine. Journal text is scored on the tablet and is not stored unless you choose to keep it.</p>
          <p className="note" style={{ marginTop: 8 }}>Typefaces: B612, made for cockpit screens, and Barlow Condensed.</p>
        </Panel>
      </div>
      <section className="panel">
        <h2 className="placard">Planned sources</h2>
        <table className="status-table left">
          <thead><tr><th scope="col">Source</th><th scope="col">Planned use</th><th scope="col">Status</th></tr></thead>
          <tbody>{data.sources.map((s) => <tr key={s.name}><th scope="row">{s.name}</th><td>{s.use}</td><td>{s.status}</td></tr>)}</tbody>
        </table>
      </section>
    </div>
  );
}
