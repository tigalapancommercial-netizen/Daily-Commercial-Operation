#!/usr/bin/env python3
"""Membuat index.html dari UI referensi Apps Script (legacy/Index.reference.html) dengan patch minimal:
jembatan google.script.run -> Supabase, URL foto Supabase Storage, teks Drive -> Supabase.
Tampilan (CSS/markup/script) selain baris di bawah TIDAK diubah."""
import sys, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
src = (root / 'legacy' / 'Index.reference.html').read_text(encoding='utf-8').replace('\r\n', '\n')

SHIM = r'''<script>
/* Jembatan Supabase: google.script.run -> window.__dcoApi (dipasang src/main.js). Antrean dipakai sampai modul siap. */
(function(){var q=[];function R(s,f){this.s=s;this.f=f;}
R.prototype.withSuccessHandler=function(fn){return new R(fn,this.f);};
R.prototype.withFailureHandler=function(fn){return new R(this.s,fn);};
R.prototype.api=function(a,p,t){var s=this.s,f=this.f;function run(){window.__dcoApi(a,p,t).then(function(r){if(s)s(r);},function(e){if(f)f(e);});}if(window.__dcoApi)run();else q.push(run);};
window.__dcoFlush=function(){while(q.length)q.shift()();};
window.google={script:{run:new R(null,null)}};
var _open=window.open;window.open=function(u){if(typeof u==='string'&&u.indexOf('#dco-backup:')===0){if(window.__dcoBackup)window.__dcoBackup(u.slice(12));return null;}return _open.apply(window,arguments);};
document.addEventListener('click',function(e){var a=e.target&&e.target.closest&&e.target.closest('a[href^="#dco-backup:"]');if(a){e.preventDefault();e.stopPropagation();if(window.__dcoBackup)window.__dcoBackup(a.getAttribute('href').slice(12));}},true);
})();
</script>
'''

PATCHES = [
  # 1. modul aplikasi (Vite) + jembatan sebelum script utama
  ('<title>Assignment Checklist Store</title>',
   '<title>Assignment Checklist Store</title>\n<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">\n<link rel="icon" type="image/svg+xml" href="/favicon.svg">\n<script type="module" src="/src/main.js"></script>'),
  ('<script>\nvar S={me:null', SHIM + '<script>\nvar S={me:null'),
  # 2. foto: Supabase Storage (path) atau ID Google Drive lama
  ("function fotoUrl(id,w){return 'https://drive.google.com/thumbnail?id='+id+'&sz=w'+(w||800);}",
   "function fotoUrl(id,w){return window.__dcoFotoUrl?window.__dcoFotoUrl(id,w):'https://drive.google.com/thumbnail?id='+id+'&sz=w'+(w||800);}"),
  ("function validId(id){return !!id&&/^[\\w-]{10,}$/.test(String(id));}",
   "function validId(id){return !!id&&(/^[\\w-]{10,}$/.test(String(id))||/^\\d{4}-\\d{2}\\/[0-9a-f]{32}_[A-Za-z0-9]{4,16}\\.(jpg|jpeg|png|webp)$/.test(String(id)));}"),
  # 3. teks yang menyebut Google Drive / Apps Script
  ('<h3>☁️ Backup ke Google Drive</h3><p class="mu">Data disalin ke Google Sheet baru di folder Drive <b>ASSIGNMENT_CHECKLIST_BACKUP</b> dengan nama',
   '<h3>☁️ Backup ke Cloud</h3><p class="mu">Data disalin ke file Excel (.xlsx — bisa dibuka di Google Sheets / Excel) yang tersimpan di <b>Supabase</b> dan langsung terunduh, dengan nama'),
  ('<label>Hapus foto Drive</label>', '<label>Hapus foto</label>'),
  ("<p class=\"mu\">Isi kolom Email di tab User, lalu jalankan fungsi <b>pasangTriggerReminder</b> sekali di editor Apps Script (kirim jam 09:00 & 16:00).</p>",
   "<p class=\"mu\">Notifikasi 🔔 di aplikasi aktif otomatis untuk Store, SPV & Master. Email reminder otomatis (jam 09:00 & 16:00) memerlukan layanan email tambahan — lihat docs/REMINDER_EMAIL.md.</p>"),
  ("Data akan DIHAPUS dari aplikasi setelah dibackup ke Drive. Lanjutkan?", "Data akan DIHAPUS dari aplikasi setelah dibackup. Lanjutkan?"),
  ("Foto di Drive tetap dipertahankan agar tautan bukti tidak putus.", "Foto tetap dipertahankan agar tautan bukti tidak putus."),
]
out = src
for old, new in PATCHES:
    n = out.count(old)
    if n != 1:
        sys.exit('PATCH GAGAL (%d kemunculan): %s' % (n, old[:80]))
    out = out.replace(old, new)
# viewport bawaan doGet Apps Script; jika sudah ada meta viewport di referensi, hindari ganda
if out.count('name="viewport"') > 1:
    out = out.replace('\n<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">', '', 1)
target = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else root / 'index.html'
target.write_text(out, encoding='utf-8')
print(target.name, 'dibuat:', len(out), 'byte,', len(PATCHES), 'patch')
