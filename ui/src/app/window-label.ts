import { getCurrentWebviewWindow } from "@tauri-apps/api/webviewWindow";

/** «Tez xarajat» mini oynasining yorlig'i (src-tauri `desktop::QUICK_WINDOW` bilan bir xil). */
export const QUICK_WINDOW_LABEL = "quick";

/**
 * Joriy Tauri oynasi yorlig'i. Tauri tashqarisida (testlar, brauzer) API yo'q — «main» qaytadi.
 * Bu `invoke` emas, oyna metama'lumoti; bindinglar qoidasiga tegmaydi.
 */
export function currentWindowLabel(): string {
  try {
    return getCurrentWebviewWindow().label;
  } catch {
    return "main";
  }
}
