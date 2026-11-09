import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { AppProvider } from "./state/app";
import fixtures from "./test/fixtures.json";

const data = fixtures as Record<string, unknown>;
const ALERT = "eng-immune-46";

beforeEach(() => {
  Element.prototype.scrollTo = () => {}; // jsdom has no layout
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const body = data[url];
      if (body === undefined) return new Response(JSON.stringify({ detail: `No fixture for ${url}` }), { status: 404 });
      return new Response(JSON.stringify(body), { status: 200 });
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.location.hash = "";
});

function open(route: string) {
  window.location.hash = route;
  render(<AppProvider><App /></AppProvider>);
}

const SCREENS: [string, string, RegExp][] = [
  ["Home", "/", /Lena Novak/],
  ["Alert detail", `/alert/${ALERT}`, /Tell the Medical Officer and run/],
  ["System detail", "/system/immune", /Body temperature/],
  ["Check-in", "/checkin", /Daily check-in/],
  ["Radiation", "/radiation", /Career dose against the limit/],
  ["Crew", "/crew", /Ana Reyes/],
  ["Ground", "/ground", /Mission control/],
  ["Call Earth", "/earth", /One-way delay/],
  ["Timeline", "/timeline", /Mission day 49/],
  ["Explainer", "/explainer", /Same heart rate/],
  ["Results", "/results", /Measured, not claimed/],
  ["Delay Theater", "/delay", /Delay Theater/],
  ["About", "/about", /Data honesty/],
  ["Admin", "/admin", /not clinical limits/],
];

describe("every screen renders with the simulated data badge", () => {
  it.each(SCREENS)("%s", async (_name, route, text) => {
    open(route);
    expect((await screen.findAllByText(text, undefined, { timeout: 3000 })).length).toBeGreaterThan(0);
    expect(screen.getByText("SIMULATED DATA")).toBeTruthy();
  });
});

it("shows a clear message for an unknown screen", async () => {
  open("/nowhere");
  expect(await screen.findByText("That screen does not exist.")).toBeTruthy();
});

it("every chart has a screen reader label", async () => {
  open("/system/immune");
  await screen.findAllByText(/Body temperature/);
  for (const svg of document.querySelectorAll("svg[role=img]")) expect(svg.getAttribute("aria-label")).toBeTruthy();
});

it("status is never color alone", async () => {
  open("/");
  await screen.findByText(/Lena Novak/);
  for (const ann of document.querySelectorAll(".ann")) expect(ann.textContent?.trim()).toBeTruthy();
});
