// Titik masuk: memasang "server" (port Code.gs) di browser untuk UI referensi Apps Script.
import { CONFIGURED, photoUrl, serverNow } from './db.js';
import { api, logoutToken, ping, A } from './server/index.js';
import { installDrafts } from './drafts.js';

const token = () => (window.S && window.S.me && window.S.me.token) || '';
const toastSafe = (m, err) => { try { window.toast(m, err); } catch (e) { alert(m); } };

// Sama seperti google.script.run: argumen diserialisasi (salinan), hasil berupa string JSON
window.__dcoFotoUrl = (id, w) => photoUrl(id, w);
window.__dcoApi = installDrafts((action, p, sesi) => api(action, JSON.parse(JSON.stringify(p == null ? {} : p)), sesi));
// A fresh Supabase server-time sync before each live camera session.
window.__dcoServerNow = () => serverNow();
window.__dcoSyncClock = () => ping();
window.__dcoBackup = (id) => {
  toastSafe('Mengunduh backup…');
  A.downloadBackup(token(), id).then((nama) => toastSafe('Backup diunduh: ' + nama, 'ok'), (e) => toastSafe(e.message || String(e), true));
};

// Keluar: cabut sesi di server juga
if (typeof window.logout === 'function') {
  const orig = window.logout;
  window.logout = function () { const t = token(); if (t) logoutToken(t); const pin = document.getElementById('lPin'); if (pin) { pin.value = ''; pin.type = 'password'; } return orig.apply(this, arguments); };
}

if (!CONFIGURED) {
  const box = document.querySelector('#vLogin .box');
  if (box) box.insertAdjacentHTML('beforeend', '<p style="margin-top:12px;color:#b91c1c;font-size:12px">Konfigurasi Supabase belum diisi (VITE_SUPABASE_URL & VITE_SUPABASE_PUBLISHABLE_KEY). Lihat README.</p>');
} else {
  ping().catch((e) => { const box = document.querySelector('#vLogin .box'); if (box) box.insertAdjacentHTML('beforeend', '<p style="margin-top:12px;color:#b91c1c;font-size:12px">' + String(e.message || e).replace(/</g, '&lt;') + '</p>'); });
}
window.__dcoFlush && window.__dcoFlush();

// Offline app-shell fallback is scoped to this GitHub Pages project; API is never cached.
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => { navigator.serviceWorker.register(import.meta.env.BASE_URL + 'dco-sw.js', { scope: import.meta.env.BASE_URL }).catch(() => {}); });
}
