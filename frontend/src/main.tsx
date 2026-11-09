import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles/tokens.css";

function App() {
  const [status, setStatus] = useState("connecting");
  useEffect(() => {
    fetch("/api/health").then((r) => r.json()).then((j) => setStatus(j.status)).catch(() => setStatus("down"));
  }, []);
  return <h1>Vigil backend: {status}</h1>;
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);

if (import.meta.env.PROD && "serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js");
