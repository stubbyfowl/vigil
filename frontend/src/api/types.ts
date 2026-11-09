export type Status = "green" | "yellow" | "red";

export interface DemoView {
  active: boolean;
  finished: boolean;
  total: number;
  index?: number;
  holding?: boolean;
  route?: string;
  caption?: string;
  astronaut?: string;
}

export interface Live {
  day: number;
  mission_days: number;
  running: boolean;
  days_per_second: number;
  version: number;
  link_up: boolean;
  demo: DemoView;
  delay_minutes: number;
  flight_seconds: number;
}

export interface Member {
  id: string;
  name: string;
  role: string;
  tag: string;
  control: boolean;
}

export interface WhyRow {
  signal: string;
  name: string;
  unit: string;
  baseline_median: number;
  baseline_low: number;
  baseline_high: number;
  current: number;
  change: number;
  days_of_drift: number;
  rule: string;
}

export interface Alert {
  id: string;
  astronaut: string;
  system: string;
  system_name: string;
  opened_day: number;
  day: number;
  level: number;
  level_reason: string;
  message: string;
  action: string;
  protocol: string;
  recheck_text: string;
  disclaimer: string;
  score: number;
  recovering?: boolean;
  why: { signals: WhyRow[]; rule: string };
}

export interface SystemCard {
  id: string;
  name: string;
  score: number;
  status: Status;
  level: number;
  confidence: number;
  learning: boolean;
  flagged: string[];
  trend: number[];
}

export interface Storm {
  phase: "none" | "active" | "passed";
  warning_hour?: number;
  onset_hour?: number;
  end_hour?: number;
  hourly?: number[];
  hourly_free?: number[];
  shelter_dose_msv?: number;
  unsheltered_dose_msv?: number;
}

export interface Radiation {
  score: number;
  status: Status;
  fraction: number;
  career_dose_msv: number;
  prior_dose_msv: number;
  mission_dose_msv: number;
  today_dose_msv: number;
  dose_rate_usv_h: number;
  peak_rate_usv_h: number;
  projected_total_msv: number;
  limit_msv: number;
  near_limit: boolean;
  storm: Storm;
  daily_dose?: number[];
  warning_usv_h?: number;
}

export interface AstronautView {
  astronaut: Member;
  day: number;
  mission_days: number;
  systems: SystemCard[];
  alerts: Alert[];
  all_clear: boolean;
  learning: boolean;
  radiation: Radiation;
}

export interface Series {
  id: string;
  name: string;
  unit: string;
  bad: string;
  cadence: number;
  decimals: number;
  days: number[];
  values: (number | null)[];
  low: (number | null)[];
  high: (number | null)[];
  median: (number | null)[];
  flagged: boolean[];
  current: number | null;
  learning: boolean;
  flagged_now: boolean;
  drift_days: number;
  recent_median: number | null;
}

export interface SystemDetail extends Omit<SystemCard, "trend" | "id"> {
  system: string;
  day: number;
  signals: Series[];
}

export interface Protocol {
  name: string;
  minutes: number;
  steps: string[];
  escalate_if: string;
}

export interface AlertDetail {
  alert: Alert;
  closed: boolean;
  charts: Series[];
  protocol?: Protocol;
  protocol_label: string;
}

export interface CrewCard extends Member {
  systems: { id: string; name: string; status: Status; learning: boolean; trend: number[] }[];
  max_level: number;
  shared_values?: Record<string, number | null>;
}

export interface GroundCard extends Member {
  systems: Record<string, Status>;
  radiation: Status;
  max_level: number;
  level3: Level3[];
}

export interface Level3 {
  id: string;
  system: string;
  level: number;
  opened_day: number;
  reason: string;
  astronaut?: string;
}

export interface Packet {
  id: number;
  kind: string;
  astronaut: string;
  title: string;
  priority: number;
  size_kb: number;
  mission_day: number;
  state: "queued" | "sent" | "in_transit" | "received";
  seconds_left: number | null;
  flight_seconds: number;
}

export interface Ground {
  day: number;
  crew: GroundCard[];
  level3: Level3[];
  packets: Packet[];
  link_up: boolean;
  delay_minutes: number;
  flight_seconds: number;
}

export interface Timeline {
  mission_days: number;
  systems: Record<string, string>;
  crew: { id: string; tag: string; name: string; control: boolean; status: Record<string, string>; level: number[] }[];
  events: { id: string; title: string; day: number; astronaut: string; system: string }[];
}
