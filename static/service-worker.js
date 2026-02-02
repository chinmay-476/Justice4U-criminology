const CACHE_NAME = 'criminology-ms-v1';
const STATIC_CACHE_NAME = 'criminology-static-v1';
const DYNAMIC_CACHE_NAME = 'criminology-dynamic-v1';

// Files to cache for offline functionality
const STATIC_FILES = [
  '/',
  '/static/css/bootstrap.min.css',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/images/favicon.ico',
  '/static/images/icon-192x192.png',
  '/static/images/icon-512x512.png',
  '/static/manifest.json',
  // AdminLTE files
  '/static/dist/css/adminlte.min.css',
  '/static/dist/js/adminlte.min.js',
  // FontAwesome
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
  // Bootstrap
  'https://cdn.jsdelivr.net/npm/bootstrap/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap/dist/js/bootstrap.bundle.min.js',
  // jQuery
  'https://code.jquery.com/jquery-3.6.0.min.js'
];

// Routes to cache dynamically
const DYNAMIC_ROUTES = [
  '/home',
  '/add_user',
  '/search_record',
  '/user_details',
  '/admin-login',
  '/super_admin_login',
  '/judge-login',
  '/about-us',
  '/contact-us'
];

// Install event - cache static files
self.addEventListener('install', event => {
  console.log('Service Worker: Installing...');
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME)
      .then(cache => {
        console.log('Service Worker: Caching static files');
        return cache.addAll(STATIC_FILES);
      })
      .catch(error => {
        console.log('Service Worker: Error caching static files', error);
      })
  );
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('Service Worker: Activating...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== STATIC_CACHE_NAME && cacheName !== DYNAMIC_CACHE_NAME) {
            console.log('Service Worker: Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip chrome-extension and other non-http requests
  if (!url.protocol.startsWith('http')) {
    return;
  }

  event.respondWith(
    caches.match(request)
      .then(response => {
        // Return cached version if available
        if (response) {
          console.log('Service Worker: Serving from cache:', request.url);
          return response;
        }

        // Otherwise fetch from network
        return fetch(request)
          .then(fetchResponse => {
            // Check if we received a valid response
            if (!fetchResponse || fetchResponse.status !== 200 || fetchResponse.type !== 'basic') {
              return fetchResponse;
            }

            // Clone the response
            const responseToCache = fetchResponse.clone();

            // Cache dynamic content
            if (shouldCacheRequest(request)) {
              caches.open(DYNAMIC_CACHE_NAME)
                .then(cache => {
                  cache.put(request, responseToCache);
                });
            }

            return fetchResponse;
          })
          .catch(error => {
            console.log('Service Worker: Fetch failed for:', request.url, error);
            
            // Return offline page for navigation requests
            if (request.mode === 'navigate') {
              return caches.match('/');
            }
            
            // Return cached version if available for other requests
            return caches.match(request);
          });
      })
  );
});

// Helper function to determine if request should be cached
function shouldCacheRequest(request) {
  const url = new URL(request.url);
  
  // Cache HTML pages
  if (request.headers.get('accept').includes('text/html')) {
    return true;
  }
  
  // Cache API responses for our domain
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/get_')) {
    return true;
  }
  
  // Cache static assets
  if (url.pathname.startsWith('/static/')) {
    return true;
  }
  
  // Cache specific routes
  return DYNAMIC_ROUTES.some(route => url.pathname === route);
}

// Background sync for form submissions
self.addEventListener('sync', event => {
  if (event.tag === 'background-sync') {
    event.waitUntil(doBackgroundSync());
  }
});

// Push notifications
self.addEventListener('push', event => {
  const options = {
    body: event.data ? event.data.text() : 'New notification from Criminology Management System',
    icon: '/static/images/icon-192x192.png',
    badge: '/static/images/icon-192x192.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'View Details',
        icon: '/static/images/icon-192x192.png'
      },
      {
        action: 'close',
        title: 'Close',
        icon: '/static/images/icon-192x192.png'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('Criminology Management System', options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', event => {
  event.notification.close();

  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/')
    );
  } else if (event.action === 'close') {
    // Just close the notification
    return;
  } else {
    // Default action - open the app
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Helper function for background sync
async function doBackgroundSync() {
  try {
    // Get pending form submissions from IndexedDB
    const pendingSubmissions = await getPendingSubmissions();
    
    for (const submission of pendingSubmissions) {
      try {
        const response = await fetch(submission.url, {
          method: submission.method,
          headers: submission.headers,
          body: submission.body
        });
        
        if (response.ok) {
          // Remove from pending submissions
          await removePendingSubmission(submission.id);
          console.log('Service Worker: Background sync successful for:', submission.url);
        }
      } catch (error) {
        console.log('Service Worker: Background sync failed for:', submission.url, error);
      }
    }
  } catch (error) {
    console.log('Service Worker: Background sync error:', error);
  }
}

// IndexedDB helper functions (simplified)
async function getPendingSubmissions() {
  // In a real implementation, you would use IndexedDB
  // For now, return empty array
  return [];
}

async function removePendingSubmission(id) {
  // In a real implementation, you would remove from IndexedDB
  console.log('Service Worker: Removing pending submission:', id);
}

// Message handler for communication with main thread
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'GET_VERSION') {
    event.ports[0].postMessage({ version: CACHE_NAME });
  }
});
