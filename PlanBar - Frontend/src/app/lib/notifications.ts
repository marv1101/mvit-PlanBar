export function requestNotificationPermission(): Promise<NotificationPermission> {
  if (!('Notification' in window)) {
    return Promise.resolve('denied');
  }
  if (Notification.permission === 'granted') {
    return Promise.resolve('granted');
  }
  if (Notification.permission === 'denied') {
    return Promise.resolve('denied');
  }
  return Notification.requestPermission();
}

export function showNotification(title: string, options?: NotificationOptions): void {
  if (!('Notification' in window)) return;
  if (Notification.permission !== 'granted') return;
  try {
    new Notification(title, {
      icon: '/favicon.ico',
      ...options,
    });
  } catch {
    // Notification failed silently
  }
}

export function showPinboardNotification(authorName: string, threadTitle: string, content: string): void {
  showNotification(`Neue Nachricht von ${authorName}`, {
    body: `In "${threadTitle}": ${content.length > 100 ? content.slice(0, 100) + '...' : content}`,
    tag: 'pinboard',
  });
}
