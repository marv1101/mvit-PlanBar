import '@testing-library/jest-dom/vitest'
import { server } from './msw-handlers'
import { beforeAll, afterEach, afterAll } from 'vitest'
import { setupIndexedDBMock, teardownIndexedDBMock } from './__mocks__/indexedDB'

if (!globalThis.crypto?.randomUUID) {
  const cryptoObj = globalThis.crypto || {};
  cryptoObj.randomUUID = cryptoObj.randomUUID || (() => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0;
      return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
  });
  (globalThis as any).crypto = cryptoObj;
}

beforeAll(() => {
  setupIndexedDBMock();
})

afterEach(() => {
  teardownIndexedDBMock();
  setupIndexedDBMock();
})

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = ResizeObserverMock as any

// Radix UI (Select etc.) relies on DOM APIs jsdom does not implement
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false
}
if (!Element.prototype.releasePointerCapture) {
  Element.prototype.releasePointerCapture = () => {}
}
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {}
}

// Mock window.matchMedia for useMediaQuery hook
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: query.includes('max-width: 768px') ? false : false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
