import "@testing-library/jest-dom/vitest";

// Onboarding (D15) testlarda standart holda o'tilgan deb olinadi; onboarding.test uni o'zi ochadi.
try {
  localStorage.setItem("baraka.onboarding", "done");
} catch {
  // jsdom'da localStorage bor; yo'q bo'lsa — dialog ko'rinadi, testlar buni hisobga oladi.
}
import { cleanup, configure } from "@testing-library/react";
import { afterEach } from "vitest";

// jsdom'da ResizeObserver yo'q, Radix (tooltip, popper) esa unga tayanadi. Test uchun bo'sh stub.
class ResizeObserverStub {
  observe(): void {
    // Testda o'lchash kerak emas.
  }
  unobserve(): void {
    // Testda o'lchash kerak emas.
  }
  disconnect(): void {
    // Testda o'lchash kerak emas.
  }
}
globalThis.ResizeObserver = ResizeObserverStub;

// findBy*/waitFor: parallel yuklama (masalan, cargo build) ostida 1 s yetmaydi — 5 s.
configure({ asyncUtilTimeout: 5000 });

// Vitest globals yoqilmagan: har testdan keyin DOM ni qo'lda tozalaymiz.
afterEach(() => {
  cleanup();
});
