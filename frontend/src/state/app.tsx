import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { get, post } from "../api/client";
import type { Live } from "../api/types";

export type Theme = "dark" | "light" | "night";

interface AppState {
  live: Live | null;
  disconnected: boolean;
  astronaut: string;
  setAstronaut: (id: string) => void;
  theme: Theme;
  setTheme: (t: Theme) => void;
  route: string;
  navigate: (path: string) => void;
}

const AppContext = createContext<AppState | null>(null);
const POLL_MS = 350;

function stored(key: string, fallback: string): string {
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

function remember(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Storage can be blocked. The choice then lasts for this visit only.
  }
}

const readRoute = () => window.location.hash.replace(/^#/, "") || "/";
export const routePath = (route: string) => route.split("?")[0];
const routeHas = (route: string, flag: string) => route.includes(`${flag}=1`);

export function AppProvider({ children }: { children: ReactNode }) {
  const [live, setLive] = useState<Live | null>(null);
  const [disconnected, setDisconnected] = useState(false);
  const [astronaut, setAstronautState] = useState(() => stored("vigil.astronaut", "eng"));
  const [theme, setThemeState] = useState<Theme>(() => stored("vigil.theme", "dark") as Theme);
  const [route, setRoute] = useState(readRoute);
  const pinned = useRef(routeHas(readRoute(), "pin"));

  useEffect(() => {
    const onHash = () => setRoute(readRoute());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const navigate = useCallback((path: string) => {
    window.location.hash = path;
  }, []);

  const setAstronaut = useCallback((id: string) => {
    remember("vigil.astronaut", id);
    setAstronautState(id);
  }, []);

  const setTheme = useCallback((t: Theme) => {
    remember("vigil.theme", t);
    setThemeState(t);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    let alive = true;
    const poll = () =>
      fetch("/api/live")
        .then(async (res) => {
          if (!res.ok) throw new Error("live");
          const data = (await res.json()) as Live;
          if (!alive) return;
          setLive(data);
          setDisconnected(res.headers.get("X-Vigil-Offline") === "1");
        })
        .catch(() => alive && setDisconnected(true));
    poll();
    const timer = setInterval(poll, POLL_MS);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (!routeHas(readRoute(), "autoplay")) return;
    window.location.hash = "/";
    post("/api/demo/start").catch(() => setDisconnected(true));
  }, []);

  const demo = live?.demo;
  useEffect(() => {
    if (!demo?.active || pinned.current) return;
    if (demo.astronaut) setAstronaut(demo.astronaut);
    if (demo.route) navigate(demo.route);
  }, [demo?.active, demo?.route, demo?.astronaut, navigate, setAstronaut]);

  return (
    <AppContext.Provider value={{ live, disconnected, astronaut, setAstronaut, theme, setTheme, route, navigate }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp(): AppState {
  const value = useContext(AppContext);
  if (!value) throw new Error("useApp must be used inside AppProvider");
  return value;
}

/** Fetch JSON whenever the path or the data version changes. Keeps old data while loading. */
export function useData<T>(path: string | null, extraKey?: unknown) {
  const { live } = useApp();
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const version = live?.version;
  const latest = useRef(0);

  const load = useCallback(() => {
    if (!path) return;
    const id = ++latest.current;
    get<T>(path)
      .then((d) => {
        if (id !== latest.current) return;
        setData(d);
        setError(null);
      })
      .catch((e: Error) => id === latest.current && setError(e.message));
  }, [path]);

  useEffect(load, [load, version, extraKey]);
  return { data, error, reload: load };
}
