import "@testing-library/jest-dom";

// jsdom in this vitest config does not provide a `localStorage` implementation
// ("localStorage is not available because --localstorage-file was not provided").
// Components such as DemoGate read `localStorage` during render via the
// useDemoStudent hook, so provide an in-memory stub. Declared `configurable` and
// `writable` so individual tests can still override it (e.g. demo-banner.test.tsx
// redefines it with Object.defineProperty).
function createLocalStorageStub(): Storage {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => (key in store ? store[key] : null),
    setItem: (key: string, value: string) => {
      store[key] = String(value);
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    key: (index: number) => Object.keys(store)[index] ?? null,
    get length() {
      return Object.keys(store).length;
    },
  } as Storage;
}

Object.defineProperty(window, "localStorage", {
  value: createLocalStorageStub(),
  configurable: true,
  writable: true,
});
