import { getCurrentWindow } from "@tauri-apps/api/window";
import { Minus, Square, X } from "lucide-react";

/** O'z sarlavha panelimiz uchun Windows uslubidagi oyna tugmalari (decorations: false). */
export function WindowControls() {
  const win = () => getCurrentWindow();
  return (
    <div className="win-controls">
      <button aria-label="Yig'ish" onClick={() => void win().minimize()}>
        <Minus size={16} strokeWidth={1.5} />
      </button>
      <button aria-label="Kattalashtirish" onClick={() => void win().toggleMaximize()}>
        <Square size={13} strokeWidth={1.5} />
      </button>
      <button className="close" aria-label="Yopish" onClick={() => void win().close()}>
        <X size={17} strokeWidth={1.5} />
      </button>
    </div>
  );
}
