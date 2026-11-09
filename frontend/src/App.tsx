import type { ReactNode } from "react";
import { Shell } from "./components/Shell";
import { Message } from "./components/Status";
import { About } from "./screens/About";
import { Admin } from "./screens/Admin";
import { AlertDetail } from "./screens/AlertDetail";
import { CheckIn } from "./screens/CheckIn";
import { Crew } from "./screens/Crew";
import { DelayTheater } from "./screens/DelayTheater";
import { Earth } from "./screens/Earth";
import { Explainer } from "./screens/Explainer";
import { Ground } from "./screens/Ground";
import { Home } from "./screens/Home";
import { Radiation } from "./screens/Radiation";
import { Results } from "./screens/Results";
import { SystemDetail } from "./screens/SystemDetail";
import { Timeline } from "./screens/Timeline";
import { routePath, useApp } from "./state/app";

function screenFor(path: string): ReactNode {
  const [, first, second] = path.split("/");
  switch (first) {
    case "": return <Home />;
    case "alert": return <AlertDetail key={second} id={second} />;
    case "system": return <SystemDetail key={second} id={second} />;
    case "checkin": return <CheckIn />;
    case "radiation": return <Radiation />;
    case "crew": return <Crew />;
    case "ground": return <Ground />;
    case "earth": return <Earth />;
    case "timeline": return <Timeline />;
    case "explainer": return <Explainer />;
    case "delay": return <DelayTheater />;
    case "results": return <Results />;
    case "about": return <About />;
    case "admin": return <Admin />;
    default: return <Message title="That screen does not exist.">Open the menu to find your way back.</Message>;
  }
}

export function App() {
  const { route } = useApp();
  return <Shell>{screenFor(routePath(route))}</Shell>;
}
