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


ICON_USER = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>'
ICON_LOCK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>'
ICON_EYE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>'
ICON_ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'

LOGIN_HTML = """<div id="vLogin" class="login">
 <section class="lg-hero">
  <i class="lg-blob b1"></i><i class="lg-blob b2"></i><i class="lg-blob b3"></i><div class="lg-grid"></div>
  <div class="lg-brand"><span class="lg-logo">⚡</span><span><b>Daily Operation</b><small>Commercial</small></span></div>
  <div class="lg-copy">
   <span class="lg-eyebrow">MAMU · TIGALAPANKAOS</span>
   <h1>Operasional 12 toko,<br><em>satu layar kendali.</em></h1>
   <p>Checklist harian, laporan DSO, rekap masalah, visiting, dan scorecard toko — dipantau langsung oleh Store, SPV Area, dan Master.</p>
   <ul class="lg-feat">
    <li><span style="--c:#6ee7b7">✓</span><div><b>Assignment Checklist Store</b><small>Tugas harian &amp; foto bukti</small></div></li>
    <li><span style="--c:#7dd3fc">⏱</span><div><b>Daily Store Operation</b><small>Opening · During · Closing · Lampu</small></div></li>
    <li><span style="--c:#fcd34d">!</span><div><b>Rekap Masalah</b><small>Action plan, PIC &amp; due date</small></div></li>
    <li><span style="--c:#f9a8d4">◎</span><div><b>Visiting &amp; Scorecard</b><small>35 poin check &amp; rating toko</small></div></li>
   </ul>
  </div>
  <div class="lg-stats"><div><b>12</b><span>Toko terpantau</span></div><div><b>4</b><span>Laporan DSO / hari</span></div><div><b>35</b><span>Poin visiting</span></div></div>
 </section>
 <section class="lg-side">
  <div class="box lg-card">
   <div class="lg-clock"><span class="lg-dot"></span><span id="lgClock">WITA</span></div>
   <h2 id="lgHello">Selamat datang 👋</h2>
   <p class="lg-sub">Masuk untuk melanjutkan ke Daily Operation Commercial.</p>
   <div class="lg-field"><label class="lbl" for="lUser">Username</label><div class="lg-in">""" + ICON_USER + """<input id="lUser" placeholder="master / spv / tk-btp / mamu-gowa …" autocomplete="username" autocapitalize="none" spellcheck="false" onkeydown="if(event.key==='Enter'){event.preventDefault();$('lPin').focus();}"></div></div>
   <div class="lg-field"><label class="lbl" for="lPin">PIN</label><div class="lg-in">""" + ICON_LOCK + """<input id="lPin" type="password" inputmode="numeric" autocomplete="current-password" placeholder="••••" onkeydown="if(event.key==='Enter')login()"><button type="button" class="lg-eye" onclick="lgEye()" aria-label="Tampilkan / sembunyikan PIN">""" + ICON_EYE + """</button></div></div>
   <button class="btn p w lg-btn" id="lgBtn" onclick="login()"><i class="lg-spin"></i><span>Masuk</span>""" + ICON_ARROW + """</button>
   <div class="lg-roles"><span>Store</span><span>SPV Area</span><span>Master</span></div>
   <p class="lg-help">Lupa PIN? Hubungi Master atau SPV Area untuk reset.</p>
  </div>
  <p class="lg-foot">🔒 Sesi aman · Data tersimpan di cloud · Zona waktu WITA</p>
 </section>
</div>

"""

LOGIN_CSS = """
/* ===== v9.1: halaman login & catatan visiting ===== */
#vLogin.login{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(380px,1fr);min-height:100vh;min-height:100dvh;padding:0;background:#f8fafc;place-items:stretch}
#vLogin .lg-hero{position:relative;overflow:hidden;isolation:isolate;color:#fff;padding:44px clamp(28px,5vw,64px);display:flex;flex-direction:column;justify-content:space-between;gap:26px;background:linear-gradient(140deg,#0f0c29 0%,#1e1b4b 32%,#4338ca 68%,#7c3aed 86%,#db2777 118%)}
#vLogin .lg-grid{position:absolute;inset:0;z-index:-1;background-image:linear-gradient(rgba(255,255,255,.07) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.07) 1px,transparent 1px);background-size:38px 38px;-webkit-mask-image:radial-gradient(ellipse at 30% 40%,#000 15%,transparent 72%);mask-image:radial-gradient(ellipse at 30% 40%,#000 15%,transparent 72%)}
#vLogin .lg-blob{position:absolute;z-index:-1;border-radius:50%;filter:blur(64px);opacity:.55;animation:lgFloat 16s ease-in-out infinite alternate}
#vLogin .b1{width:380px;height:380px;background:#db2777;right:-90px;top:-70px}
#vLogin .b2{width:330px;height:330px;background:#06b6d4;left:-100px;bottom:-80px;animation-delay:-5s}
#vLogin .b3{width:260px;height:260px;background:#a78bfa;left:42%;top:42%;animation-delay:-9s}
@keyframes lgFloat{0%{transform:translate(0,0) scale(1)}50%{transform:translate(34px,-26px) scale(1.08)}100%{transform:translate(-22px,22px) scale(.95)}}
#vLogin .lg-brand{display:flex;align-items:center;gap:12px}
#vLogin .lg-logo{width:46px;height:46px;border-radius:14px;display:grid;place-items:center;font-size:22px;background:linear-gradient(135deg,#8b5cf6,#ec4899);box-shadow:0 10px 26px rgba(236,72,153,.45),inset 0 1px 0 rgba(255,255,255,.35)}
#vLogin .lg-brand b{display:block;font-size:17px;letter-spacing:-.01em}#vLogin .lg-brand small{display:block;font-size:12px;color:#c7d2fe}
#vLogin .lg-eyebrow{display:inline-flex;font-size:11px;font-weight:800;letter-spacing:.22em;color:#c7d2fe;padding:6px 12px;border:1px solid rgba(255,255,255,.18);border-radius:999px;background:rgba(255,255,255,.06);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px)}
#vLogin .lg-copy h1{font-size:clamp(30px,3.5vw,48px);line-height:1.07;letter-spacing:-.035em;margin:18px 0 14px;font-weight:800}
#vLogin .lg-copy h1 em{font-style:normal;background:linear-gradient(90deg,#f9a8d4,#c4b5fd,#67e8f9);-webkit-background-clip:text;background-clip:text;color:transparent}
#vLogin .lg-copy p{color:#dbe2ff;max-width:520px;font-size:14.5px;margin:0 0 22px}
#vLogin .lg-feat{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;max-width:640px}
#vLogin .lg-feat li{display:flex;gap:11px;align-items:center;padding:12px 13px;border-radius:14px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.13);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);transition:.25s}
#vLogin .lg-feat li:hover{background:rgba(255,255,255,.14);transform:translateY(-2px)}
#vLogin .lg-feat span{flex:0 0 34px;height:34px;border-radius:10px;display:grid;place-items:center;font-weight:900;color:#1e1b4b;background:var(--c);box-shadow:0 6px 16px rgba(0,0,0,.22)}
#vLogin .lg-feat b{display:block;font-size:13px}#vLogin .lg-feat small{display:block;font-size:11.5px;color:#c7d2fe}
#vLogin .lg-stats{display:flex;gap:12px;flex-wrap:wrap}
#vLogin .lg-stats div{padding:10px 16px;border-radius:14px;background:rgba(15,12,41,.35);border:1px solid rgba(255,255,255,.12)}
#vLogin .lg-stats b{font-size:22px;display:block;letter-spacing:-.02em}#vLogin .lg-stats span{font-size:11px;color:#c7d2fe}
#vLogin .lg-side{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:32px 24px;gap:16px;background:radial-gradient(circle at 85% 8%,#e0e7ff 0,transparent 45%),radial-gradient(circle at 8% 92%,#fce7f3 0,transparent 42%),#f8fafc}
#vLogin .lg-card{max-width:410px;max-height:none;overflow:visible;padding:30px 28px;border-radius:24px;background:#fff;box-shadow:0 30px 70px rgba(30,27,75,.16),0 2px 8px rgba(30,27,75,.06);border:1px solid #eef0f8;animation:lgIn .55s cubic-bezier(.2,.8,.2,1)}
@keyframes lgIn{from{opacity:0;transform:translateY(16px) scale(.98)}}
#vLogin .lg-clock{display:inline-flex;align-items:center;gap:8px;font-size:11.5px;font-weight:700;color:#4338ca;background:#eef2ff;padding:6px 11px;border-radius:999px}
#vLogin .lg-dot{width:7px;height:7px;border-radius:50%;background:#22c55e;animation:lgPulse 2s infinite}
@keyframes lgPulse{0%{box-shadow:0 0 0 0 rgba(34,197,94,.55)}70%{box-shadow:0 0 0 8px rgba(34,197,94,0)}100%{box-shadow:0 0 0 0 rgba(34,197,94,0)}}
#vLogin .lg-card h2{margin:16px 0 4px;font-size:26px;letter-spacing:-.03em;background:none;-webkit-background-clip:border-box;background-clip:border-box;color:#0f172a}
#vLogin .lg-sub{margin:0 0 20px;color:#64748b;font-size:13px}
#vLogin .lg-field{margin-bottom:14px}
#vLogin .lg-in{position:relative;display:flex;align-items:center}
#vLogin .lg-in>svg{position:absolute;left:14px;width:18px;height:18px;color:#94a3b8;pointer-events:none;transition:.2s}
#vLogin .lg-in input{width:100%;height:50px;padding:0 48px 0 44px;border:1.5px solid #e2e8f0;border-radius:14px;background:#f8fafc;font-size:14.5px;font-weight:600;color:#0f172a;outline:none;transition:.2s}
#vLogin .lg-in input::placeholder{color:#a3adbf;font-weight:500}
#vLogin .lg-in input:focus{border-color:#6366f1;background:#fff;box-shadow:0 0 0 4px rgba(99,102,241,.15)}
#vLogin .lg-in:focus-within>svg{color:#4f46e5}
#vLogin .lg-eye{position:absolute;right:7px;width:36px;height:36px;border:0;background:transparent;border-radius:10px;color:#64748b;cursor:pointer;display:grid;place-items:center;padding:0}
#vLogin .lg-eye:hover{background:#eef2ff;color:#4f46e5}#vLogin .lg-eye svg{width:18px;height:18px}
#vLogin .lg-btn{position:relative;overflow:hidden;height:52px;border-radius:14px;font-size:15px;font-weight:800;margin-top:6px;gap:10px;background:linear-gradient(135deg,#4f46e5,#7c3aed 55%,#db2777);box-shadow:0 14px 30px rgba(79,70,229,.35);transition:transform .15s,box-shadow .2s}
#vLogin .lg-btn:hover{transform:translateY(-1px);box-shadow:0 18px 36px rgba(79,70,229,.45)}
#vLogin .lg-btn:active{transform:translateY(0)}
#vLogin .lg-btn:after{content:"";position:absolute;inset:0;background:linear-gradient(110deg,transparent 30%,rgba(255,255,255,.32) 50%,transparent 70%);transform:translateX(-100%);animation:lgShine 3.4s infinite}
@keyframes lgShine{60%,100%{transform:translateX(100%)}}
#vLogin .lg-btn svg{width:18px;height:18px;transition:transform .2s}#vLogin .lg-btn:hover svg{transform:translateX(3px)}
#vLogin .lg-spin{display:none;width:18px;height:18px;border-radius:50%;border:2.5px solid rgba(255,255,255,.45);border-top-color:#fff;animation:lgRot .7s linear infinite}
#vLogin .lg-btn.busy{pointer-events:none;opacity:.9}#vLogin .lg-btn.busy .lg-spin{display:inline-block}#vLogin .lg-btn.busy svg{display:none}
@keyframes lgRot{to{transform:rotate(360deg)}}
#vLogin .lg-roles{display:flex;gap:6px;justify-content:center;margin:18px 0 0;flex-wrap:wrap}
#vLogin .lg-roles span{font-size:11px;font-weight:700;padding:5px 11px;border-radius:999px}
#vLogin .lg-roles span:nth-child(1){background:#dcfce7;color:#15803d}#vLogin .lg-roles span:nth-child(2){background:#e0e7ff;color:#4338ca}#vLogin .lg-roles span:nth-child(3){background:#fce7f3;color:#be185d}
#vLogin .lg-help{margin:12px 0 0;text-align:center;font-size:12px;color:#94a3b8}
#vLogin .lg-foot{font-size:11.5px;color:#94a3b8;margin:0;text-align:center}
@media(max-width:900px){#vLogin.login{grid-template-columns:1fr;align-content:start}#vLogin .lg-hero{padding:26px 22px 76px;gap:14px;justify-content:flex-start}#vLogin .lg-feat,#vLogin .lg-stats{display:none}#vLogin .lg-copy h1{font-size:28px;margin:12px 0 8px}#vLogin .lg-copy p{font-size:13px;margin:0}#vLogin .lg-side{margin-top:-58px;padding:0 16px 24px;justify-content:flex-start;background:transparent;position:relative;z-index:1}#vLogin .lg-card{padding:24px 20px}}
@media(prefers-reduced-motion:reduce){#vLogin *{animation:none!important;transition:none!important}}
.v9-note{margin-top:10px}.v9-note textarea{width:100%;min-height:76px;resize:vertical;display:block}
"""

LOGIN_JS = """// ===== v9.1: login =====
function lgEye(){var i=$('lPin');i.type=i.type==='password'?'text':'password';i.focus();}
(function(){var el=$('lgClock'),h=$('lgHello');if(!el)return;var tick=function(){try{var d=new Date(),t=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Makassar',hour:'2-digit',minute:'2-digit',hour12:false}).format(d),f=new Intl.DateTimeFormat('id-ID',{timeZone:'Asia/Makassar',weekday:'long',day:'numeric',month:'long',year:'numeric'}).format(d),hh=+t.slice(0,2);
  el.textContent=t+' WITA · '+f;h.textContent=(hh<11?'Selamat pagi':hh<15?'Selamat siang':hh<18?'Selamat sore':'Selamat malam')+' 👋';}catch(e){}};tick();setInterval(tick,30000);})();
try{var lgLast=localStorage.getItem('ac_last_user');if(lgLast&&$('lUser'))$('lUser').value=lgLast;}catch(e){}
var lgLoginBase=login;login=function(){var b=$('lgBtn'),u=$('lUser').value;if(b){if(b.classList.contains('busy'))return;b.classList.add('busy');}
  var done=function(){if(b)b.classList.remove('busy');},p=lgLoginBase.apply(this,arguments);
  if(p&&p.then)p.then(function(){try{localStorage.setItem('ac_last_user',String(u).trim());}catch(e){}done();},done);else done();return p;};
"""

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

  # ===================== v9.1 — permintaan user 12 Nov 2026 =====================
  # 4. Menu STORE hanya: Assignment Checklist Store, Daily Store Operation, Rekap Masalah. SPV: semua kecuali Pengaturan. Master: semua.
  ("NAV.splice(6,0,['issues'", "var STORE_TABS=['ceklis','dso','MASALAH'];\nNAV.splice(6,0,['issues'"),
  ("var nav=NAV.filter(function(n){return n[3]===''||(n[3]==='mgr'&&isMgr())||(n[3]==='mst'&&isMaster());});",
   "var nav=NAV.filter(function(n){return isMgr()?(n[3]!=='mst'||isMaster()):STORE_TABS.indexOf(n[0])>=0;});"),
  ("fillFilters();go('dash');loadNotif();", "fillFilters();go(isMgr()?'dash':'ceklis');loadNotif();"),
  ("function go(t){S.tab=t;", "function go(t){if(S.me&&!isMgr()&&STORE_TABS.indexOf(t)<0)t='ceklis';S.tab=t;"),
  # 5. Dashboard: hapus banner "Executive Control Center" (tanggal pantau tetap ada di tab 02 · Kepatuhan)
  ("var html='<div class=\"exec-root\">'+header+nav;", "var html='<div class=\"exec-root\">'+nav;"),
  # 6. Visiting: hapus foto per seksi (kolase maks 4), kolom catatan seksi dibuat lebar penuh
  ("""h+='<div class="row" style="margin-top:8px"><div style="flex:2"><span class="lbl">Catatan '+esc(x.nama)+'</span><input value="'+esc(v.catatan[x.kode]||'')+'" '+(ro?'disabled':'')+' onchange="S.vis.catatan[\\''+x.kode+'\\']=this.value"></div><div style="flex:1"><span class="lbl">Foto (kolase maks 4)</span><div style="display:flex;gap:6px;align-items:center">'+thumbs([v.foto[x.kode]],36)+(ro?'':(v.foto[x.kode]?'<button class="btn s" onclick="delete S.vis.foto[\\''+x.kode+'\\'];renderVisit()">✕</button>':'')+'<label class="btn s">📷<input type="file" accept="image/*" multiple style="display:none" onchange="visitFoto(\\''+x.kode+'\\',this)"></label>')+'</div></div></div>';""",
   """h+='<div class="v9-note"><span class="lbl">Catatan '+esc(x.nama)+'</span><textarea '+(ro?'disabled':'')+' placeholder="Tulis catatan / temuan '+esc(x.nama)+'…" onchange="S.vis.catatan[\\''+x.kode+'\\']=this.value">'+esc(v.catatan[x.kode]||'')+'</textarea></div>';"""),
  # 7. Login baru
  ("function login(){call('login'", "function login(){return call('login'"),
  ('BETWEEN', '<div id="vLogin" class="login">', '<div id="vApp"', LOGIN_HTML),
  ('</style>', LOGIN_CSS + '</style>'),
  ("(function(){try{var m=localStorage.getItem('ac_me');", LOGIN_JS + "(function(){try{var m=localStorage.getItem('ac_me');"),
]
out = src
for patch in PATCHES:
    if patch[0] == 'BETWEEN':
        _, a, b, new = patch
        i = out.find(a); j = out.find(b, i + 1)
        if out.count(a) != 1 or i < 0 or j < 0:
            sys.exit('PATCH GAGAL (BETWEEN): %s' % a[:80])
        out = out[:i] + new + out[j:]
        continue
    old, new = patch
    n = out.count(old)
    if n != 1:
        sys.exit('PATCH GAGAL (%d kemunculan): %s' % (n, old[:80]))
    out = out.replace(old, new)
# viewport bawaan doGet Apps Script; jika sudah ada meta viewport di referensi, hindari ganda
if out.count('name="viewport"') > 1:
    out = out.replace('\n<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">', '', 1)
from patch_v10_photo_nav import patch_html
out = patch_html(out)
from patch_v11_compact import patch_html as patch_v11
out = patch_v11(out)
from patch_v12_before_after import patch_html as patch_v12
out = patch_v12(out)
from patch_v13_dso_timestamp import patch_html as patch_v13
out = patch_v13(out)
from patch_v14_assignment_autocheck import patch_html as patch_v14
out = patch_v14(out)
target = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else root / 'index.html'
target.write_text(out, encoding='utf-8')
print(target.name, 'dibuat:', len(out), 'byte,', len(PATCHES), 'patch')
