self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',e=>e.waitUntil(clients.claim()));
self.addEventListener('message',e=>{
  const ms=Math.max(0,e.data.end-Date.now());
  e.waitUntil(new Promise(r=>setTimeout(r,ms)).then(async()=>{
    const late=Date.now()-e.data.end;
    await self.registration.showNotification('Rest over (service worker)',{body:'late '+late+' ms',tag:'rest-sw',requireInteraction:true,renotify:true,vibrate:[400,200,400]});
    (await clients.matchAll()).forEach(c=>c.postMessage('SW timer fired, late '+late+' ms'));
  }));
});
self.addEventListener('notificationclick',e=>{e.notification.close();e.waitUntil(clients.matchAll({type:'window'}).then(c=>c[0]?c[0].focus():clients.openWindow('./')))});
