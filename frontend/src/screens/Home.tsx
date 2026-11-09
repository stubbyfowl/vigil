import { useEffect, useRef, useState } from "react";
import type { AstronautView, SystemCard } from "../api/types";
import { Sparkline } from "../components/Charts";
import { Annunciator, LevelBadge, LoadState } from "../components/Status";
import { useApp, useData } from "../state/app";

function Card({ s, labels }: { s: SystemCard; labels: Record<string, string> }) {
  const { navigate } = useApp();
  const moved = s.flagged.map((id) => labels[id] ?? id).join(", ");
  return (
    <button className="card" data-system={s.id} onClick={() => navigate(`/system/${s.id}`)} aria-label={`${s.name}. Open details.`}>
      <div className="card-head">
        <h2>{s.name}</h2>
        {s.learning ? <span className="placard">Learning</span> : <Annunciator status={s.status} />}
      </div>
      <div className="score">
        <b>{s.learning ? "--" : s.score}</b>
        <span className="placard">drift / 100</span>
      </div>
      <Sparkline values={s.trend} label={s.name} height={150} />
      <div className="moved">{s.learning ? "Learning your normal" : moved ? `Moved: ${moved}` : "Inside your normal"}</div>
      <div className="confidence">
        <span className="placard">Confidence</span>
        <span className="meter"><i style={{ width: `${s.confidence * 100}%` }} /></span>
        <span className="mono">{Math.round(s.confidence * 100)}%</span>
      </div>
    </button>
  );
}

function Status({ view }: { view: AstronautView }) {
  const { navigate } = useApp();
  if (view.learning) {
    return (
      <div className="master" data-level="1">
        <div className="master-word">LEARNING</div>
        <p>Vigil is learning your normal. It will not raise alerts until it has enough days of readings.</p>
      </div>
    );
  }
  if (view.all_clear) {
    const watching = view.systems.filter((s) => s.status !== "green").map((s) => s.name);
    if (watching.length > 0) {
      return (
        <div className="master" data-level="1">
          <div className="master-word">WATCHING</div>
          <p>No alerts. {watching.join(" and ")} moved a little from your normal. Vigil is keeping an eye on it.</p>
        </div>
      );
    }
    return (
      <div className="master" data-level="0">
        <div className="master-word">ALL CLEAR</div>
        <p>Every system is inside your own normal today.</p>
      </div>
    );
  }
  const top = view.alerts[0];
  const more = view.alerts.length - 1;
  return (
    <button className="alert-strip" data-level={top.level} onClick={() => navigate(`/alert/${top.id}`)} aria-label={`Open alert. ${top.message}`}>
      <div className="stack">
        <div className="master-word" style={{ fontSize: 48 }}>{view.alerts.length} ALERT{view.alerts.length > 1 ? "S" : ""}</div>
        <LevelBadge level={top.level} />
      </div>
      <div className="msg">{top.message}</div>
      {more > 0 && <span className="placard">+{more} more</span>}
    </button>
  );
}

export function Home() {
  const { live, astronaut, navigate } = useApp();
  const { data, error } = useData<AstronautView>(live ? `/api/astronaut/${astronaut}?day=${live.day}` : null);
  const labels = useData<{ signals: { id: string; name: string }[] }>("/api/crew").data;
  const names = Object.fromEntries((labels?.signals ?? []).map((s) => [s.id, s.name]));
  const scroller = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(0);

  const scrollTo = (i: number) => {
    const card = scroller.current?.children[i] as HTMLElement | undefined;
    scroller.current?.scrollTo({ left: card ? card.offsetLeft - scroller.current.offsetLeft : 0, behavior: "smooth" });
  };

  const onScroll = () => {
    const el = scroller.current;
    if (!el) return;
    const first = el.children[0] as HTMLElement | undefined;
    const step = first ? first.offsetWidth + 14 : 1;
    setActive(Math.round(el.scrollLeft / step));
  };

  const worst = data ? [...data.systems].sort((a, b) => b.score - a.score)[0] : undefined;
  const worstIndex = data && worst && worst.status !== "green" ? data.systems.findIndex((s) => s.id === worst.id) : -1;
  useEffect(() => {
    if (worstIndex >= 0) scrollTo(worstIndex);
  }, [worstIndex, astronaut]);

  if (!data) return <LoadState error={error} />;
  return (
    <div className="home">
      <div className="hero">
        <div className="who">
          <h1>{data.astronaut.name}</h1>
          <p>{data.astronaut.role}</p>
        </div>
        <Status view={data} />
      </div>
      <div className="cards" ref={scroller} onScroll={onScroll}>
        {data.systems.map((s) => <Card key={s.id} s={s} labels={names} />)}
      </div>
      <div className="dots">
        {data.systems.map((s, i) => (
          <button key={s.id} className="dot" aria-label={`Show ${s.name}`} aria-current={i === active} onClick={() => scrollTo(i)}><i /></button>
        ))}
      </div>
      <nav className="home-actions" aria-label="Main actions">
        <button className="btn" onClick={() => navigate("/checkin")}>Check-in</button>
        <button className="btn" onClick={() => navigate("/radiation")}>Radiation</button>
        <button className="btn" onClick={() => navigate("/crew")}>Crew</button>
        <button className="btn primary" onClick={() => navigate("/earth")}>Call Earth</button>
      </nav>
    </div>
  );
}
