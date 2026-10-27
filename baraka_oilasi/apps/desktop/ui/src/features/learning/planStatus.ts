/** Holat o'tishlari tugmalari (yadro `transition` qoidasi bilan bir xil; yopilgan reja — tugmasiz). Uy va Musofir rejalari uchun umumiy. */
export const NEXT: Record<string, string[]> = {
  ACTIVE: ["PAUSED", "DONE", "DROPPED"],
  PAUSED: ["ACTIVE", "DONE", "DROPPED"],
};
export const STATUS_TONE: Record<string, string> = { ACTIVE: "border-accent text-accent-text", PAUSED: "border-warn text-warn" };
