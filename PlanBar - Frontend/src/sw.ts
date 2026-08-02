/// <reference lib="webworker" />

import { precacheAndRoute } from 'workbox-precaching';
import { NetworkFirst } from 'workbox-strategies';
import { registerRoute } from 'workbox-routing';

declare const self: ServiceWorkerGlobalScope;

precacheAndRoute(self.__WB_MANIFEST);

registerRoute(
  ({ url }) => url.pathname.startsWith('/api/'),
  new NetworkFirst({
    cacheName: 'api-cache',
    networkTimeoutSeconds: 5,
  }),
);

self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key.startsWith('workbox-precache') === false && key.includes('api-cache') === false)
          .map((key) => caches.delete(key))
      )
    ).then(() => clients.claim())
  );
});

self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

const OFFLINE_ACTIONS_CACHE = 'planbar-offline-actions';

self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-offline-actions') {
    event.waitUntil(processOfflineActions());
  } else if (event.tag === 'sync-initial-data') {
    event.waitUntil(syncInitialData());
  }
});

async function processOfflineActions() {
  const clientList = await self.clients.matchAll();
  for (const client of clientList) {
    client.postMessage({ type: 'PROCESS_OFFLINE_QUEUE' });
  }
}

async function syncInitialData() {
  const clientList = await self.clients.matchAll();
  for (const client of clientList) {
    client.postMessage({ type: 'SYNC_INITIAL_DATA' });
  }
}

self.addEventListener('push', (event) => {
  let data: { title: string; body: string; url: string; tag: string } = {
    title: 'PlanBar',
    body: '',
    url: '/',
    tag: 'default',
  };
  try {
    if (event.data) {
      const parsed = event.data.json();
      data = {
        title: parsed.title || data.title,
        body: parsed.body || '',
        url: parsed.url || '/',
        tag: parsed.tag || 'default',
      };
    }
  } catch {
    data.body = event.data?.text() || '';
  }

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/favicon.png',
      badge: '/favicon.png',
      tag: data.tag,
      data: { url: data.url },
      vibrate: [200, 100, 200],
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const urlToOpen = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.startsWith(self.location.origin) && 'focus' in client) {
          client.navigate(urlToOpen);
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    }),
  );
});
