/* Smart Solution analytics and masked Webvisor, only after explicit consent. */
(function () {
  'use strict';
  if (location.hostname !== 'smart-soultion.com' && location.hostname !== 'www.smart-soultion.com') return;
  var ID = 113756904, KEY = 'ss-analytics-consent-v2', GOOGLE_KEY = 'ss-google-analytics-consent-v1', GOOGLE_TAG = 'G-0YX4ML38RM', enabled = false, googleStarted = false, groupReady = false;
  // Earlier consent explicitly excluded replay. Ask again before recording;
  // preserve earlier refusals instead of asking those visitors repeatedly.
  function stored() { try { return localStorage.getItem(KEY) || (localStorage.getItem('ss-analytics-consent-v1') === 'no' ? 'no' : null); } catch (_) { return null; } }
  function googleChoice() { try { return localStorage.getItem(GOOGLE_KEY); } catch (_) { return null; } }
  function rememberBoth(value) {
    try {
      localStorage.setItem(KEY, value);
      localStorage.setItem(GOOGLE_KEY, value);
      return localStorage.getItem(KEY) === value && localStorage.getItem(GOOGLE_KEY) === value;
    } catch (_) {
      try { localStorage.setItem(KEY, 'no'); localStorage.setItem(GOOGLE_KEY, 'no'); } catch (_) {}
      return false;
    }
  }
  function goal(name) { if (enabled && typeof window.ym === 'function') window.ym(ID, 'reachGoal', name); try { if (googleChoice() === 'yes' && typeof window.gtag === 'function') window.gtag('event', name); } catch (_) {} }
  function start() {
    if (enabled || !groupReady || stored() !== 'yes') return;
    enabled = true;
    window.ym = window.ym || function () { (window.ym.a = window.ym.a || []).push(arguments); };
    window.ym.l = Date.now();
    var tag = document.createElement('script'); tag.async = true; tag.src = 'https://mc.yandex.ru/metrika/tag.js';
    document.head.appendChild(tag);
    var ref = ''; try { ref = document.referrer ? new URL(document.referrer).origin : ''; } catch (_) {}
    window.ym(ID, 'init', { clickmap: true, trackLinks: false, accurateTrackBounce: true,
      webvisor: true, ecommerce: false, url: location.origin + location.pathname, referrer: ref });
    if (location.pathname.indexOf('/services/') === 0 && location.pathname !== '/services/') goal('service_view');
  }
  function startGoogle() {
    if (googleStarted || !groupReady || googleChoice() !== 'yes') return;
    googleStarted = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
    var path = location.pathname;
    if (!/^\/(?:|team\/?|services\/?|services\/[a-z0-9-]+\/?)$/.test(path)) path = '/other';
    var ref = ''; try { ref = document.referrer ? new URL(document.referrer).origin : ''; } catch (_) {}
    window.gtag('js', new Date());
    window.gtag('config', GOOGLE_TAG, {send_page_view: false, allow_google_signals: false, allow_ad_personalization_signals: false,
      page_location: location.origin + path, page_referrer: ref});
    window.gtag('event', 'page_view', {page_location: location.origin + path, page_title: 'Smart Solution', page_referrer: ref});
    var script = document.createElement('script'); script.async = true;
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + GOOGLE_TAG;
    document.head.appendChild(script);
    if (location.pathname.indexOf('/services/') === 0 && location.pathname !== '/services/') window.gtag('event', 'service_view');
  }
  var style = document.createElement('style');
  style.textContent = [
    '.ss-consent{box-sizing:border-box;position:fixed;z-index:10000;left:24px;bottom:24px;width:430px;max-width:calc(100vw - 48px);padding:26px;background:#111;color:#f7f7f7;border:1px solid #333;border-radius:20px;box-shadow:0 18px 70px #0003;font:14px/1.6 var(--ft,system-ui);animation:ss-cookie-in .25s ease-out}',
    '.ss-consent .ss-cookie-label{display:flex;align-items:center;gap:10px;color:#f19b9c;font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;margin-bottom:16px}.ss-cookie-mark{display:grid;place-items:center;width:30px;height:30px;border-radius:10px;background:#e52124;color:#fff;font-size:20px;letter-spacing:0}',
    '.ss-consent h2{font:800 26px/1.15 var(--fh,system-ui);letter-spacing:-.04em;margin:0 0 12px;max-width:14em}.ss-consent p{margin:0 0 16px;color:#c9c9c9}.ss-consent details{margin:0 0 18px;color:#c9c9c9;font-size:12px}.ss-consent summary{cursor:pointer;text-decoration:underline;text-underline-offset:3px}.ss-consent details p{margin:10px 0 0}',
    '.ss-cookie-actions{display:flex;flex-wrap:wrap;gap:10px}.ss-cookie-actions button{flex:1}.ss-consent button{min-height:46px;padding:10px 12px;border-radius:10px;border:1px solid #777;background:#fff;color:#111;cursor:pointer;font:700 13px/1.3 var(--ft,system-ui);transition:background .2s}.ss-consent .yes{background:#e52124;border-color:#e52124;color:#fff}.ss-consent .yes:hover{background:#c8161c}.ss-consent .no:hover{background:#eaeaea}.ss-consent button:focus-visible,.ss-consent summary:focus-visible{outline:3px solid #fff;outline-offset:4px}',
    '.ss-consent .ss-cookie-note{font-size:11px;color:#aaa;margin:14px 0 0}.ss-analytics-settings{position:fixed;z-index:59;left:20px;bottom:20px;padding:9px 13px;border:1px solid #ddd;border-radius:99px;background:#fffc;color:#444;box-shadow:0 2px 15px #0001;font:600 11px var(--ft,system-ui);cursor:pointer;backdrop-filter:blur(12px)}.ss-analytics-settings[hidden]{display:none}',
    '@keyframes ss-cookie-in{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}@media(max-width:600px){.ss-consent{left:12px;bottom:88px;width:calc(100vw - 24px);max-width:none;padding:22px;max-height:calc(100svh - 110px);overflow:auto;border-radius:18px}.ss-consent h2{font-size:24px}.ss-analytics-settings{left:12px;bottom:24px}.ss-cookie-actions{gap:8px}}@media(prefers-reduced-motion:reduce){.ss-consent{animation:none}}'
  ].join('');
  // The new assistant is a full-width pill on phones. Keep settings in the
  // footer there, rather than placing a second control over that pill.
  style.textContent += '.ss-analytics-settings{position:static;display:block;margin:18px auto;width:max-content;max-width:calc(100% - 24px)}@media(max-width:600px){.ss-analytics-settings{margin-bottom:96px}}';
  document.head.appendChild(style);
  var panel;
  function show(manage) {
    if (panel) panel.remove();
    panel = document.createElement('section'); panel.className = 'ss-consent'; panel.setAttribute('aria-label', 'Настройки аналитики');
    settings.hidden = true;
    panel.innerHTML = '<div class="ss-cookie-label"><span class="ss-cookie-mark" aria-hidden="true">◌</span>SMART COOKIE</div><h2>Немного cookie.<br>Больше пользы.</h2><p>С вашего разрешения Яндекс Метрика и Google Analytics помогут нам улучшать сайт. Данные Google могут передаваться за пределы России.</p><details><summary>Что именно мы собираем</summary><p>Посещения, клики и записи действий на странице — Вебвизор. Содержимое полей и переписка с помощником скрыты от записи. До согласия аналитика не загружается.</p></details><div class="ss-cookie-actions">' + (manage ? '<button class="no" type="button">Отозвать согласие</button>' : '') + '<button class="yes" type="button">Принять</button>' + (manage ? '<button class="close" type="button">Закрыть</button>' : '') + '</div><p class="ss-cookie-note">Без аналитики сайт тоже работает. Выбор можно изменить в Cookie-настройках внизу страницы.</p>';
    panel.querySelector('.yes').onclick = function () { if (!rememberBoth('yes')) return; start(); startGoogle(); panel.remove(); panel = null; settings.hidden = false; };
    if (manage) {
      panel.querySelector('.no').onclick = function () { if (!rememberBoth('no')) return; if (enabled && typeof window.ym === 'function') window.ym(ID, 'destruct'); location.reload(); };
      panel.querySelector('.close').onclick = function () { panel.remove(); panel = null; settings.hidden = false; };
    }
    document.body.appendChild(panel);
  }
  var settings = document.createElement('button'); settings.type = 'button'; settings.className = 'ss-analytics-settings';
  settings.textContent = 'Cookie-настройки'; settings.onclick = function () { show(true); }; (document.querySelector('footer') || document.body).appendChild(settings);
  if ((stored() !== 'yes' && stored() !== 'no') || (googleChoice() !== 'yes' && googleChoice() !== 'no')) show(false);
  // Apply privacy masking before either vendor can start.
  var group = document.createElement('script'); group.src = '/assets/group-analytics.js?v=20261118-parity1';
  group.onload = function () { groupReady = true; start(); startGoogle(); };
  document.head.appendChild(group);
  window.addEventListener('storage', function (event) {
    if ((event.key === KEY || event.key === GOOGLE_KEY) && event.oldValue === 'yes' && event.newValue !== 'yes') location.reload();
  });
  document.addEventListener('click', function (e) {
    var el = e.target.closest('a,button'); if (!el) return;
    if ((el.id === 'as-dock' || el.id === 'as-pin') && el.getAttribute('aria-expanded') === 'true') goal('assistant_open');
    if (el.tagName === 'A') {
      var href = el.getAttribute('href') || '';
      if (/^https:\/\/t\.me\//.test(href)) goal('telegram_click');
    }
  });
  window.addEventListener('ss:form-telegram-open', function () { goal('form_telegram_open'); });
})();
