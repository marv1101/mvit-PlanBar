import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockApi = {
  get: vi.fn(),
  post: vi.fn(),
  delete: vi.fn(),
}

vi.mock('../app/lib/api', () => ({
  default: mockApi,
}))

const mockSubscription = {
  endpoint: 'https://example.com/push/test',
  toJSON: () => ({
    endpoint: 'https://example.com/push/test',
    keys: { p256dh: 'p256dh_key', auth: 'auth_key' },
  }),
}

const mockPushManager = {
  getSubscription: vi.fn(),
  subscribe: vi.fn().mockResolvedValue(mockSubscription),
}

const mockServiceWorkerRegistration = {
  pushManager: mockPushManager,
}

const mockServiceWorker = {
  ready: Promise.resolve(mockServiceWorkerRegistration),
}

beforeEach(() => {
  vi.clearAllMocks()

  Object.assign(globalThis, {
    Notification: {
      permission: 'default',
      requestPermission: vi.fn().mockResolvedValue('granted'),
    },
    navigator: {
      serviceWorker: mockServiceWorker,
    },
  })
})

describe('pushService', () => {
  describe('onPushStateChange', () => {
    it('registers a listener and returns an unsubscribe function', async () => {
      const { onPushStateChange } = await import('../app/services/pushService')
      const listener = vi.fn()
      const unsubscribe = onPushStateChange(listener)

      expect(typeof unsubscribe).toBe('function')
      unsubscribe()
    })
  })

  describe('initPushState', () => {
    it('detects push support and initial state', async () => {
      const { initPushState, onPushStateChange } = await import('../app/services/pushService')
      const stateListener = vi.fn()
      onPushStateChange(stateListener)

      await initPushState()

      expect(mockPushManager.getSubscription).toHaveBeenCalled()
    })
  })

  describe('subscribeToPush', () => {
    it('requests permission and subscribes', async () => {
      mockApi.get.mockResolvedValue({ data: { public_key: 'test_public_key' } })
      mockApi.post.mockResolvedValue({ status: 201 })
      mockPushManager.getSubscription.mockResolvedValue(null)

      const { subscribeToPush } = await import('../app/services/pushService')
      const result = await subscribeToPush()

      expect(result).toBe(true)
      expect(Notification.requestPermission).toHaveBeenCalled()
      expect(mockApi.get).toHaveBeenCalledWith('/push/vapid-public-key')
      expect(mockPushManager.subscribe).toHaveBeenCalledWith({
        userVisibleOnly: true,
        applicationServerKey: expect.any(Uint8Array),
      })
      expect(mockApi.post).toHaveBeenCalledWith('/push/subscription', {
        endpoint: 'https://example.com/push/test',
        p256dh_key: 'p256dh_key',
        auth_key: 'auth_key',
        device_type: 'web',
      })
    })

    it('returns false when permission is denied', async () => {
      Object.assign(globalThis, {
        Notification: {
          permission: 'denied',
        },
      })

      const { subscribeToPush } = await import('../app/services/pushService')
      const result = await subscribeToPush()
      expect(result).toBe(false)
    })

    it('returns false on API failure', async () => {
      mockApi.get.mockRejectedValue(new Error('Network error'))
      mockPushManager.getSubscription.mockResolvedValue(null)

      const { subscribeToPush } = await import('../app/services/pushService')
      const result = await subscribeToPush()
      expect(result).toBe(false)
    })
  })

  describe('unsubscribeFromPush', () => {
    it('unsubscribes and removes subscription from backend', async () => {
      const sub = {
        endpoint: 'https://example.com/push/test',
        unsubscribe: vi.fn().mockResolvedValue(undefined),
      }
      mockPushManager.getSubscription.mockResolvedValue(sub)
      mockApi.delete.mockResolvedValue({ status: 204 })

      const { unsubscribeFromPush } = await import('../app/services/pushService')
      const result = await unsubscribeFromPush()

      expect(result).toBe(true)
      expect(sub.unsubscribe).toHaveBeenCalled()
      expect(mockApi.delete).toHaveBeenCalledWith('/push/subscription', {
        params: { endpoint: 'https://example.com/push/test' },
      })
    })
  })
})
