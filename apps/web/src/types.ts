export type ViewKey =
  | "chat"
  | "matches"
  | "players"
  | "tactics"
  | "reports";

export type RightPanelTab = "tactics" | "evidence";

export type BoardTool = "select" | "arrow" | "zone" | "player" | "erase";

export interface BoardPlayer {
  id: string;
  number: number;
  x: number;
  y: number;
  role: "home" | "focus" | "opponent";
  label: string;
  displayLabel?: string;
  findingRefs?: string[];
}

export interface BoardArrow {
  id: string;
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  kind: "movement" | "passing";
  label?: string;
  findingRefs?: string[];
}

export interface BoardZone {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  label?: string;
  findingRefs?: string[];
}
