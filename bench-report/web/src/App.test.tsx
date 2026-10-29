// The front end on the payload the API gives on the snapshot of the gold tables (scripts/snapshot_fixtures.py --web).
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import App from "./App";
import payload from "./__fixtures__/perio_bench.dq.json";

const BENCHES = [
  { key: "perio_bench", name: "PerioBench", tagline: "Trustworthy records", summary: "", status: "live",
    gold_schema: "gold_perio_bench", reports: [{ key: "dq", title: payload.title, summary: "" }] },
  { key: "oral_health_bench", name: "OralHealthBench", tagline: "Accurate AI answers", summary: "Score the AI.",
    status: "planned", gold_schema: "gold_oral_health_bench", reports: [] },
  { key: "access_bench", name: "AccessBench", tagline: "Getting care", summary: "", status: "exploratory",
    gold_schema: "gold_access_bench", reports: [] },
];

beforeEach(() => {
  window.location.hash = "";
  vi.stubGlobal("fetch", vi.fn(async (url: string) => ({
    ok: true, json: async () => (url === "/api/benches" ? BENCHES : payload),
  })));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

test("opens on the first bench with a report, says synthetic, and shows the five domains", async () => {
  render(<App />);
  expect(await screen.findByRole("heading", { name: payload.title })).toBeTruthy();
  expect(screen.getByText(/Synthetic data/)).toBeTruthy();
  const all = payload.tiles.All;
  expect(within(screen.getByTestId("tile-Completeness")).getByText(String(all.completeness.value))).toBeTruthy();
  expect(within(screen.getByTestId("tile-Reliability")).getByText("Not assessed")).toBeTruthy();
});

test("the clinic filter changes the completeness tile", async () => {
  render(<App />);
  const select = await screen.findByLabelText("Clinic");
  fireEvent.change(select, { target: { value: "6" } });
  const six = payload.tiles["6"].completeness.value;
  expect(within(screen.getByTestId("tile-Completeness")).getByText(String(six))).toBeTruthy();
});

test("benches are tabs in bench order, and one without a report says what it's waiting for", async () => {
  render(<App />);
  const tabs = await screen.findAllByRole("tab");
  expect(tabs.map(t => t.textContent)).toEqual(["PerioBench", "OralHealthBenchplanned", "AccessBenchexploratory"]);
  fireEvent.click(tabs[1]);
  expect(await screen.findByText(/No report yet/)).toBeTruthy();
  expect(screen.getByText("gold_oral_health_bench")).toBeTruthy();
});
