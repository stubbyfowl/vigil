import { useRef, useState, type ReactNode } from "react";
import { post } from "../api/client";
import { useApp, type Theme } from "../state/app";
import { useCrew } from "../state/crew";

const LINKS: [string, string][] = [
  ["/", "Home"],
  ["/timeline", "Mission timeline"],
  ["/explainer", "Why personal baselines"],
  ["/delay", "Delay Theater"],
  ["/results", "Results"],
  ["/ground", "Ground screen"],
  ["/about", "About and honesty"],
];
const THEMES: Theme[] = ["dark", "light", "night"];
const ADMIN_TAPS = 5;

function Menu({ close }: { close: () => void }) {
  const { navigate, theme, setTheme } = useApp();
  const go = (path: string) => {
    navigate(path);
    close();
  };
  return (
    <div className="scrim" onClick={close}>
      <div className="sheet" role="dialog" aria-label="Menu" onClick={(e) => e.stopPropagation()}>
        <button className="btn primary" onClick={() => { post("/api/demo/start"); close(); }}>Play demo</button>
        {LINKS.map(([path, label]) => (
          <button key={path} className="btn" onClick={() => go(path)}>{label}</button>
        ))}
        <h2 className="placard">Display</h2>
        <div className="row">
          {THEMES.map((t) => (
            <button key={t} className="btn grow" aria-pressed={t === theme} onClick={() => setTheme(t)}>{t}</button>
          ))}
        </div>
      </div>
    </div>
  );
}

function Director() {
  const { live } = useApp();
  const demo = live?.demo;
  if (!demo?.active) return null;
  return (
    <div className="director" role="status" aria-live="polite">
      <span className="placard">Demo {(demo.index ?? 0) + 1} of {demo.total}</span>
      <p>{demo.caption}</p>
      <button className="btn" onClick={() => post("/api/demo/next")}>Next beat</button>
      <button className="btn" onClick={() => post("/api/demo/stop")}>Stop</button>
    </div>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  const { live, disconnected, astronaut, setAstronaut, navigate } = useApp();
  const crew = useCrew();
  const [menu, setMenu] = useState(false);
  const taps = useRef(0);

  const tapWordmark = () => {
    taps.current += 1;
    if (taps.current >= ADMIN_TAPS) {
      taps.current = 0;
      navigate("/admin");
    } else {
      navigate("/");
    }
  };

  return (
    <div className="app">
      <header className="topbar">
        <button className="wordmark" onClick={tapWordmark} aria-label="Vigil home">VIGIL</button>
        <nav className="crew-switch" aria-label="Choose crew member">
          {crew.map((m) => (
            <button key={m.id} className="btn" aria-label={m.name} aria-pressed={m.id === astronaut} style={{ padding: "0 10px" }} onClick={() => setAstronaut(m.id)}>
              {m.tag}
            </button>
          ))}
        </nav>
        <span className="spacer" />
        <div className="sim-badge">SIMULATED DATA</div>
        <div className="indicator" role="status">
          <span>{live?.link_up === false ? "Link lost" : "Link up"}</span>
          <span>{live ? `${live.delay_minutes} min delay` : ""}</span>
        </div>
        <button className="met" onClick={() => navigate("/timeline")} aria-label="Open mission timeline">
          <span className="placard">Mission day</span>
          <b>{live ? `${String(live.day).padStart(3, "0")}/${live.mission_days}` : "---"}</b>
        </button>
        <button className="btn" onClick={() => setMenu(true)} aria-haspopup="dialog">Menu</button>
      </header>
      {disconnected && <div className="banner" role="alert">No connection to the Vigil server. Showing the last known data. Start it with: make dev</div>}
      <main className={`main${live?.demo.active ? " with-director" : ""}`}>{children}</main>
      <Director />
      {menu && <Menu close={() => setMenu(false)} />}
    </div>
  );
}

export function Back({ to = "/", label = "Back" }: { to?: string; label?: string }) {
  const { navigate } = useApp();
  return <button className="btn back" onClick={() => navigate(to)}>{label}</button>;
}
