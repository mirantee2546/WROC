// ชื่อของ Cache (สามารถตั้งเป็นชื่อโปรเจกต์คุณได้)
const CACHE_NAME = 'wroc-cache-v1';

// ไฟล์ที่ต้องการให้โหลดเร็วขึ้น (ใส่เท่าที่จำเป็นก่อน)
const urlsToCache = [
  '/',
  '/static/img/icon.png'
];

// ขั้นตอนการติดตั้ง Service Worker
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

// การดึงข้อมูล (Fetch) - ช่วยให้แอปทำงานได้เสถียรขึ้น
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        return response || fetch(event.request);
      })
  );
});