import api from '../lib/api';

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
}

export type PushPermission = 'granted' | 'denied' | 'prompt' | 'unsupported';

export interface PushState {
  permission: PushPermission;
  subscribed: boolean;
  registration: ServiceWorkerRegistration | null;
}

type StateListener = (state: PushState) => void;
const listeners = new Set<StateListener>();

let cachedState: PushState = {
  permission: 'unsupported',
  subscribed: false,
  registration: null,
};

function notifyListeners() {
  listeners.forEach((fn) => fn(cachedState));
}

export function onPushStateChange(fn: StateListener): () => void {
  listeners.add(fn);
  fn(cachedState);
  return () => listeners.delete(fn);
}

async function updateState() {
  const supported = 'serviceWorker' in navigator && 'PushManager' in window;
  if (!supported) {
    cachedState = { permission: 'unsupported', subscribed: false, registration: null };
    notifyListeners();
    return;
  }
  const permission = Notification.permission as PushPermission;
  let registration: ServiceWorkerRegistration | null = null;
  let subscribed = false;
  try {
    registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    subscribed = !!subscription;
  } catch {
    // service worker not ready yet
  }
  cachedState = { permission, subscribed, registration };
  notifyListeners();
}

export async function initPushState(): Promise<void> {
  await updateState();
}

export async function subscribeToPush(): Promise<boolean> {
  if (cachedState.permission === 'unsupported') return false;

  if (Notification.permission === 'denied') return false;

  if (Notification.permission === 'default') {
    const result = await Notification.requestPermission();
    if (result !== 'granted') {
      await updateState();
      return false;
    }
  }

  try {
    const { data: keyData } = await api.get('/push/vapid-public-key');
    const publicKey = keyData.public_key;

    const registration = await navigator.serviceWorker.ready;
    let subscription = await registration.pushManager.getSubscription();

    if (!subscription) {
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      });
    }

    const subJson = subscription.toJSON();
    await api.post('/push/subscription', {
      endpoint: subJson.endpoint,
      p256dh_key: subJson.keys?.p256dh ?? '',
      auth_key: subJson.keys?.auth ?? '',
      device_type: 'web',
    });

    await updateState();
    return true;
  } catch (err) {
    console.error('[Push] Subscribe failed:', err);
    await updateState();
    return false;
  }
}

export async function unsubscribeFromPush(): Promise<boolean> {
  try {
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();

    if (subscription) {
      const endpoint = subscription.endpoint;
      await subscription.unsubscribe();

      try {
        await api.delete('/push/subscription', {
          params: { endpoint },
        });
      } catch {
        // backend cleanup not critical
      }
    }

    await updateState();
    return true;
  } catch (err) {
    console.error('[Push] Unsubscribe failed:', err);
    return false;
  }
}
