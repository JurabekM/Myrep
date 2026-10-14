import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
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

// Vitest globals yoqilmagan: har testdan keyin DOM ni qo'lda tozalaymiz.
afterEach(() => {
  cleanup();
});
