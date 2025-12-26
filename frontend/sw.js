/**
 * STOCKMAN - Service Worker
 * Handles push notifications and offline caching
 */

const CACHE_NAME = 'stockman-v1';
const ASSETS_TO_CACHE = [
    '/',
    '/index.html',
    '/css/styles.css',
    '/js/app.js',
    '/manifest.json'
];

// ============================================
// Install Event
// ============================================

self.addEventListener('install', (event) => {
    console.log('[SW] Installing...');

    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[SW] Caching assets');
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );

    // Activate immediately
    self.skipWaiting();
});

// ============================================
// Activate Event
// ============================================

self.addEventListener('activate', (event) => {
    console.log('[SW] Activating...');

    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        })
    );

    // Take control of all pages
    self.clients.claim();
});

// ============================================
// Fetch Event (Network first, fallback to cache)
// ============================================

self.addEventListener('fetch', (event) => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') return;

    // Skip API requests (always fetch from network)
    if (event.request.url.includes('/api/')) return;

    event.respondWith(
        fetch(event.request)
            .then((response) => {
                // Clone and cache the response
                const responseClone = response.clone();
                caches.open(CACHE_NAME).then((cache) => {
                    cache.put(event.request, responseClone);
                });
                return response;
            })
            .catch(() => {
                // Fallback to cache
                return caches.match(event.request);
            })
    );
});

// ============================================
// Push Notifications
// ============================================

self.addEventListener('push', (event) => {
    console.log('[SW] Push received');

    let data = {
        title: 'Stockman',
        body: 'You have a new update!',
        icon: '/icons/icon-192.png',
        badge: '/icons/icon-72.png',
        data: { url: '/' }
    };

    if (event.data) {
        try {
            data = { ...data, ...event.data.json() };
        } catch (e) {
            data.body = event.data.text();
        }
    }

    const options = {
        body: data.body,
        icon: data.icon,
        badge: data.badge,
        vibrate: [100, 50, 100],
        data: data.data,
        actions: [
            { action: 'open', title: 'Open Stockman' },
            { action: 'dismiss', title: 'Dismiss' }
        ],
        requireInteraction: false,
        tag: 'stockman-notification'
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// ============================================
// Notification Click
// ============================================

self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Notification clicked');

    event.notification.close();

    if (event.action === 'dismiss') return;

    const urlToOpen = event.notification.data?.url || '/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                // If app is already open, focus it
                for (const client of clientList) {
                    if (client.url.includes(self.location.origin) && 'focus' in client) {
                        return client.focus();
                    }
                }
                // Otherwise open new window
                return clients.openWindow(urlToOpen);
            })
    );
});

// ============================================
// Background Sync (for offline messages)
// ============================================

self.addEventListener('sync', (event) => {
    if (event.tag === 'send-message') {
        console.log('[SW] Syncing messages...');
        // Could implement offline message queue here
    }
});
