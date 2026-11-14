import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./i18n";
import "./styles/globals.css";
import { App } from "./app/App";

const container = document.getElementById("root");
if (container === null) {
  throw new Error("#root elementi topilmadi — index.html ni tekshiring");
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
