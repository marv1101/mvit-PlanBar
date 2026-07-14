const SW_URL = '/sw.js';

type RegisterSWOptions = {
  onUpdate?: (registration: ServiceWorkerRegistration) => void;
  onSuccess?: (registration: ServiceWorkerRegistration) => void;
  onError?: (error: unknown) => void;
};

export async function registerServiceWorker(options?: RegisterSWOptions): Promise<ServiceWorkerRegistration | null> {
  if (!('serviceWorker' in navigator)) {
    return null;
  }

  try {
    const registration = await navigator.serviceWorker.register(SW_URL, {
      scope: '/',
      updateViaCache: 'none',
    });

    if (registration.installing) {
      registration.installing.addEventListener('statechange', () => {
        if (registration.active && options?.onSuccess) {
          options.onSuccess(registration);
        }
      });
    }

    registration.addEventListener('updatefound', () => {
      const newWorker = registration.installing;
      if (!newWorker) return;

      newWorker.addEventListener('statechange', () => {
        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
          if (options?.onUpdate) {
            options.onUpdate(registration);
          }
        }
      });
    });

    return registration;
  } catch (err) {
    if (options?.onError) {
      options.onError(err);
    }
    return null;
  }
}

export async function unregisterServiceWorker(): Promise<boolean> {
  if (!('serviceWorker' in navigator)) {
    return false;
  }
  const registrations = await navigator.serviceWorker.getRegistrations();
  for (const registration of registrations) {
    await registration.unregister();
  }
  return true;
}

export function isServiceWorkerSupported(): boolean {
  return 'serviceWorker' in navigator;
}

export function isBackgroundSyncSupported(): boolean {
  return 'SyncManager' in self;
}

export async function getServiceWorkerRegistration(): Promise<ServiceWorkerRegistration | null> {
  if (!('serviceWorker' in navigator)) {
    return null;
  }
  return navigator.serviceWorker.getRegistration('/');
}
