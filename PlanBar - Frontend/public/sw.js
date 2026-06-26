const CACHE_VERSION = 'planbar-v1';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const API_CACHE = `${CACHE_VERSION}-api`;
const DYNAMIC_CACHE = `${CACHE_VERSION}-dynamic`;

const STATIC_ASSETS = [
  '/',
  '/index.html',
];

const API_PATTERN = /^\/api\//;

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    }).then(() => {
      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => key.startsWith('planbar-') && key !== STATIC_CACHE && key !== API_CACHE && key !== DYNAMIC_CACHE)
          .map((key) => caches.delete(key))
      );
    }).then(() => {
      return self.clients.claim();
    })
  );
});

function shouldCache(url) {
  try {
    const parsed = new URL(url);
    if (parsed.pathname.startsWith('/api/v1/users/login') ||
        parsed.pathname.startsWith('/api/v1/users/refresh') ||
        parsed.pathname.startsWith('/api/v1/users/logout')) {
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== 'GET') {
    return;
  }

  if (url.pathname.startsWith('/api/')) {
    if (!shouldCache(url.href)) {
      return;
    }
    event.respondWith(networkFirstWithCache(request.clone()));
    return;
  }

  if (
    url.pathname.startsWith('/assets/') ||
    url.pathname.match(/\.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?|ttf|eot)$/)
  ) {
    event.respondWith(cacheFirst(request.clone()));
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(networkFirstWithCache(request.clone()));
    return;
  }
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) {
    return cached;
  }
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return caches.match('/');
  }
}

async function networkFirstWithCache(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(API_CACHE);
      cache.put(request, response.clone());
      const cloned = response.clone();
      const body = await cloned.text();
      const headers = {};
      cloned.headers.forEach((value, key) => {
        headers[key] = value;
      });
      const cacheBody = new Response(body, {
        status: response.status,
        statusText: response.statusText,
        headers,
      });
      cache.put(request, cacheBody);
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }
    if (request.mode === 'navigate') {
      return caches.match('/');
    }
    return new Response(
      JSON.stringify({ error: 'offline', detail: 'Du bist offline. Diese Daten sind nicht im Cache verfügbar.' }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json', 'X-PlanBar-Offline': 'true' },
      }
    );
  }
}

self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-offline-actions') {
    event.waitUntil(processOfflineActions());
  } else if (event.tag === 'sync-initial-data') {
    event.waitUntil(syncInitialData());
  }
});

async function processOfflineActions() {
  const channels = await self.clients.matchAll();
  for (const client of channels) {
    client.postMessage({ type: 'PROCESS_OFFLINE_QUEUE' });
  }
}

async function syncInitialData() {
  const channels = await self.clients.matchAll();
  for (const client of channels) {
    client.postMessage({ type: 'SYNC_INITIAL_DATA' });
  }
}

self.addEventListener('push', (event) => {
  if (!event.data) return;
  try {
    const data = event.data.json();
    const options = {
      body: data.message || '',
      icon: '/favicon.ico',
      badge: '/favicon.ico',
      data: {
        url: data.url || '/',
        ...data,
      },
    };
    event.waitUntil(
      self.registration.showNotification(data.title || 'PlanBar', options)
    );
  } catch {
    const text = event.data.text();
    event.waitUntil(
      self.registration.showNotification('PlanBar', { body: text, icon: '/favicon.ico' })
    );
  }
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url === url && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(url);
      }
    })
  );
});
