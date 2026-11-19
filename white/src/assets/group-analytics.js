/* Shared event contract. No vendor requests or replay initialization before consent. */
(function () {
  'use strict';
  if (window.__groupAnalyticsInstalled) return;
  var host = location.hostname.replace(/^www\./, ''), config;
  if (host === 'smart-soultion.com') config = ['smart',113756904,'ss-analytics-consent-v2','ss-google-analytics-consent-v1'];
  if (host === 'vedal-med.ru') config = ['vedal',112490942,'vedal.analytics.v2','vedal.google.analytics.v1'];
  if (host === 'c3ag.ru') config = ['c3ag',114300351,'c3ag.analytics.consent.v2'];
  if (host === 'astor-ai.ru') config = ['astor_site',114340712,'astor.site.analytics.v1'];
  if (host === 'globe.176-123-165-162.nip.io' || host === 'app.astor-ai.ru') config = ['astor_app',113931017,'astor.analytics.yandex.v1','astor.analytics.google.v1'];
  if (!config) return;
  window.__groupAnalyticsInstalled = true;
  function choice() {
    try {
      if (config[0] === 'c3ag' || config[0] === 'astor_site') return JSON.parse(localStorage.getItem(config[2]) || '{}');
      return {yandex:['yes','granted'].indexOf(localStorage.getItem(config[2])) >= 0, google:localStorage.getItem(config[3]) === 'yes'};
    } catch (_) { return {}; }
  }
  function emit(name, params) {
    var consent = choice(), data = Object.assign({site_surface:config[0]}, params || {});
    if (consent.yandex && typeof window.ym === 'function') window.ym(config[1], 'reachGoal', name, data);
    if (consent.google && typeof window.gtag === 'function') window.gtag('event', name, data);
  }
  // Mark private containers BEFORE loading Webvisor, including future React/chat DOM.
  function mask(root) {
    if (!root || !root.querySelectorAll) return;
    var selectors = 'form,input,textarea,[contenteditable="true"],[role="log"],.clio-panel,.clio-sheet,.clio-messages,#as-panel,#as-chat,#chatWidget,#chatLog,.assistant-panel,[data-analytics-private]';
    if (root.matches && root.matches(selectors)) root.classList.add('ym-hide-content','ym-disable-keys');
    root.querySelectorAll(selectors).forEach(function (el) { el.classList.add('ym-hide-content','ym-disable-keys'); });
  }
  mask(document);
  new MutationObserver(function (changes) {
    changes.forEach(function (change) { change.addedNodes.forEach(function (node) {
      if (node.nodeType !== 1) return;
      if (node.matches('form,input,textarea,[contenteditable="true"],[role="log"]')) node.classList.add('ym-hide-content','ym-disable-keys');
      mask(node);
    }); });
  }).observe(document.documentElement,{childList:true,subtree:true});
  var path = location.pathname, depths = {}, forms = new WeakSet(), videos = new WeakMap();
  function route() { if (path !== location.pathname) { path = location.pathname; depths = {}; } }
  document.addEventListener('scroll',function () {
    route();
    var height = document.documentElement.scrollHeight, viewport = innerHeight;
    if (height <= viewport || (!choice().yandex && !choice().google)) return;
    var depth = Math.min(100,Math.round((scrollY + viewport) / height * 100));
    [25,50,75,90,100].forEach(function (n) { if (depth >= n && !depths[n]) { depths[n] = true; emit('scroll_depth',{percent_scrolled:n}); } });
  },{passive:true});
  document.addEventListener('click',function (event) {
    var target = event.target instanceof Element ? event.target.closest('a') : null;
    if (!target) return;
    var raw = target.getAttribute('href') || '', channel = /^tel:/i.test(raw) ? 'phone' : /^mailto:/i.test(raw) ? 'email' : /^https:\/\/(t\.me|telegram\.me)\//i.test(raw) ? 'telegram' : /^https:\/\/(wa\.me|api\.whatsapp\.com)\//i.test(raw) ? 'whatsapp' : null;
    if (channel) { emit('contact_click',{contact_channel:channel}); return; }
    try {
      var url = new URL(raw,location.origin);
      if (!/^https?:$/.test(url.protocol)) return;
      var ext = url.pathname.match(/\.(pdf|docx?|xlsx?|pptx?|zip|csv)$/i);
      if (ext) emit('download_click',{file_extension:ext[1].toLowerCase()});
      if (url.origin !== location.origin) emit('outbound_click',{link_domain:url.hostname});
    } catch (_) {}
  });
  document.addEventListener('focusin',function (event) {
    var form = event.target instanceof Element ? event.target.closest('form') : null;
    if (form && !forms.has(form) && (choice().yandex || choice().google)) { forms.add(form); emit('form_start'); }
  });
  document.addEventListener('submit',function () { emit('form_submit_attempt'); },true);
  ['play','timeupdate','ended'].forEach(function (type) { document.addEventListener(type,function (event) {
    var video = event.target;
    if (!(video instanceof HTMLVideoElement) || video.autoplay || video.loop || video.getAttribute('aria-hidden') === 'true') return;
    if (!choice().yandex && !choice().google) return;
    var reached = videos.get(video) || {}; videos.set(video,reached);
    if (type === 'play' && !reached.start) { reached.start = true; emit('video_start'); }
    if (type === 'ended' && !reached.end) { reached.end = true; emit('video_complete'); }
    if (type === 'timeupdate' && Number.isFinite(video.duration) && video.duration > 0) [25,50,75].forEach(function (n) {
      if (video.currentTime / video.duration * 100 >= n && !reached[n]) { reached[n] = true; emit('video_progress',{video_percent:n}); }
    });
  },true); });
})();
