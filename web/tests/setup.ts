import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

class RO { observe() {} unobserve() {} disconnect() {} }
(globalThis as unknown as { ResizeObserver: typeof RO }).ResizeObserver = RO;
if (!HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
}
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: (globalThis as { __push?: (p: string) => void }).__push ?? (() => {}), replace: () => {} }),
  usePathname: () => "/",
}));
afterEach(() => cleanup());
