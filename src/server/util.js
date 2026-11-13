// Konstanta & utilitas — salinan 1:1 dari Code.gs v6 (Apps Script)
import { serverNow } from '../db.js';

export const SRC_MASALAH_ID = '1jcv1DwjmPNkSb7oG1TtVyTsDJbE4KK-AIpRJc3G94UY';
export const TOKO_AWAL = ['TIGALAPANKAOS BTP', 'MAMU BTP', 'MAMU PALOPO', 'TIGALAPANKAOS PALU', 'MAMU TAMALATE', 'TIGALAPANKAOS MANADO',
  'TIGALAPANKAOS SAMARINDA', 'MAMU KENDARI', 'TIGALAPANKAOS POLMAN', 'TIGALAPANKAOS BONE', 'MAMU GOWA', 'TIGALAPANKAOS TORAJA'];

export const DEFAULT_CFG = {
  kategori: ['Operasional', 'Stok & Inventory', 'Sales & Target', 'Customer Service', 'SDM & Disiplin', 'Visual Merchandising', 'Fasilitas & Aset', 'IT & Sistem', 'Marketing & Promo', 'Lainnya'],
  prioritas: ['Kritis', 'Tinggi', 'Sedang', 'Rendah'],
  status: ['Open', 'On Progress', 'Pending', 'Selesai', 'Dibatalkan'],
  dsoForms: [{ id: 'OPENING', nama: 'Opening Report', batas: '09:30' }, { id: 'DURING', nama: 'During Operation Report', batas: '15:00' },
    { id: 'CLOSING', nama: 'Closing Report', batas: '23:30' }, { id: 'LAMPU', nama: 'Report Lampu', batas: '18:30' }],
  slaValidasiJam: 3, jamKerjaMulai: 8, jamKerjaSelesai: 21,
  rating: { Excellent: 95, Good: 85, 'Need Improvement': 75 },
  visitSeksi: [{ kode: 'A', nama: 'Finance' }, { kode: 'B', nama: 'Asset & GA' }, { kode: 'C', nama: 'Merchandise' }, { kode: 'D', nama: 'Human Resources' }, { kode: 'E', nama: 'Warehouse' }],
  bobot: { ceklis: 25, lapor: 15, dso: 30, visit: 20, masalah: 10 },
  minIssueVisit: 15,
};

export const SCHEMA = {
  TOKO: [['nama', 'Nama Toko'], ['area', 'Area'], ['aktif', 'Aktif']],
  USERS: [['username', 'Username'], ['pin', 'PIN'], ['role', 'Role (MASTER/SPV/STORE)'], ['toko', 'Toko'], ['nama', 'Nama Tampil'], ['email', 'Email (untuk reminder)']],
  CONFIG: [['key', 'Key'], ['value', 'Value (JSON)']],
  MASALAH: [['id', 'ID'], ['tanggal', 'Tanggal Briefing'], ['toko', 'Toko'], ['sesi', 'Sesi / Jam'], ['pemimpin', 'Pemimpin Briefing'], ['peserta', 'Peserta / Jumlah'], ['kategori', 'Kategori'],
    ['masalah', 'Masalah / Temuan'], ['akar', 'Akar Penyebab'], ['solusi', 'Solusi / Action Plan'], ['pic', 'PIC'], ['dueDate', 'Due Date'], ['prioritas', 'Prioritas'], ['status', 'Status'],
    ['progress', 'Progress (%)'], ['tglSelesai', 'Tanggal Selesai'], ['update', 'Update / Kendala / Follow-up'], ['linkBukti', 'Link Bukti'], ['fotoId', 'Foto ID'], ['validasi', 'Validasi SPV'],
    ['validasiOleh', 'Validasi Oleh'], ['validasiTgl', 'Validasi Tgl'], ['dibuatOleh', 'Dilapor Oleh'], ['updateTgl', 'Update Terakhir'], ['updateOleh', 'Update Oleh'], ['idLama', 'ID Lama']],
  TUGAS: [['id', 'ID'], ['tanggal', 'Tanggal Dibuat'], ['toko', 'Toko'], ['judul', 'Judul Tugas'], ['deskripsi', 'Deskripsi'], ['kategori', 'Kategori'], ['prioritas', 'Prioritas'], ['dueDate', 'Due Date'], ['pic', 'PIC'],
    ['status', 'Status'], ['progress', 'Progress (%)'], ['tglSelesai', 'Tanggal Selesai'], ['catatan', 'Catatan Toko'], ['fotoId', 'Foto ID'], ['validasi', 'Validasi SPV'], ['validasiOleh', 'Validasi Oleh'],
    ['validasiTgl', 'Validasi Tgl'], ['dibuatOleh', 'Dibuat Oleh'], ['updateTgl', 'Update Terakhir'], ['updateOleh', 'Update Oleh']],
  RUTIN: [['id', 'ID'], ['judul', 'Judul'], ['deskripsi', 'Deskripsi'], ['kategori', 'Kategori'], ['prioritas', 'Prioritas'], ['pic', 'PIC'], ['frekuensi', 'Frekuensi'], ['hari', 'Hari/Tanggal'],
    ['toko', 'Toko (SEMUA atau A|B|C)'], ['aktif', 'Aktif'], ['dibuatOleh', 'Dibuat Oleh'], ['updateTgl', 'Update Terakhir'], ['interval', 'Interval (Periodik, hari)'], ['mulai', 'Mulai (Periodik)']],
  CEKLIS: [['id', 'ID'], ['tanggal', 'Tanggal'], ['toko', 'Toko'], ['rutinId', 'Rutin ID'], ['judul', 'Judul'], ['status', 'Status'], ['jam', 'Jam Centang'], ['catatan', 'Catatan'], ['fotoId', 'Foto ID'],
    ['validasi', 'Validasi SPV'], ['validasiOleh', 'Validasi Oleh'], ['validasiTgl', 'Validasi Tgl'], ['updateTgl', 'Update Terakhir'], ['updateOleh', 'Update Oleh']],
  FORM_DEF: [['id', 'ID'], ['form', 'Form'], ['urutan', 'Urutan'], ['label', 'Label Item'], ['deskripsi', 'Keterangan Foto'], ['multi', 'Kolase (Y/N)'], ['wajib', 'Wajib (Y/N)'], ['aktif', 'Aktif']],
  DSO: [['id', 'ID'], ['tanggal', 'Tanggal'], ['toko', 'Toko'], ['form', 'Form'], ['waktuSubmit', 'Waktu Submit'], ['oleh', 'Nama Pengisi'], ['jawaban', 'Jawaban (JSON itemId:fotoId)'], ['keterangan', 'Keterangan'],
    ['slaSubmit', 'SLA Submit'], ['validasi', 'Validasi SPV'], ['validasiOleh', 'Validasi Oleh'], ['validasiTgl', 'Validasi Tgl'], ['ketSpv', 'Keterangan SPV'], ['slaValidasi', 'SLA Validasi'],
    ['updateTgl', 'Update Terakhir'], ['updateOleh', 'Update Oleh']],
  VISIT_DEF: [['id', 'ID'], ['seksi', 'Seksi'], ['kode', 'Kode'], ['label', 'Label Item'], ['aktif', 'Aktif']],
  JADWAL: [['id', 'ID'], ['tanggal', 'Tanggal'], ['toko', 'Toko'], ['pic', 'PIC'], ['jamMulai', 'Jam Mulai'], ['jamSelesai', 'Jam Selesai'], ['agenda', 'Agenda / Tugas di Toko'], ['status', 'Status'], ['catatan', 'Catatan Hasil'], ['dibuatOleh', 'Dibuat Oleh'], ['updateTgl', 'Update Terakhir']],
  VISIT: [['id', 'ID'], ['tanggal', 'Visit Date'], ['minggu', 'Week'], ['toko', 'Store'], ['leader', 'Leader In Charge'], ['evaluator', 'Evaluator'], ['tipe', 'Visit Type'], ['jawaban', 'Jawaban (JSON)'],
    ['catatan', 'Catatan Seksi (JSON)'], ['foto', 'Foto Seksi (JSON)'], ['issues', 'List Issue'], ['skor', 'Skor Seksi (JSON)'], ['finalScore', 'Final Score'], ['rating', 'Rating'], ['totalPass', 'Total Pass'],
    ['totalDinilai', 'Total Dinilai'], ['validasi', 'Validasi Manager'], ['validasiOleh', 'Validasi Oleh'], ['validasiTgl', 'Validasi Tgl'], ['updateTemuan', 'Update Temuan (JSON)'], ['keterangan', 'Keterangan'],
    ['updateTgl', 'Update Terakhir'], ['updateOleh', 'Update Oleh']],
  VISIT_ISSUE: [['id', 'Issue ID'], ['visitId', 'Visit ID'], ['tanggal', 'Tanggal Visit'], ['toko', 'Toko'], ['pointId', 'Kode Point'], ['seksi', 'Seksi'],
    ['issue', 'Temuan / Issue'], ['akar', 'Akar Penyebab'], ['action', 'Action Plan'], ['pic', 'PIC'], ['dueDate', 'Due Date'],
    ['prioritas', 'Prioritas'], ['status', 'Status'], ['progress', 'Progress (%)'], ['fotoId', 'Foto Bukti'], ['validasi', 'Validasi SPV'],
    ['validasiOleh', 'Divalidasi Oleh'], ['validasiTgl', 'Tanggal Validasi'], ['updateTgl', 'Update Terakhir'], ['updateOleh', 'Update Oleh'],
    ['fotoAfter', 'Foto Sesudah (Update)'], ['updateNote', 'Catatan Perbaikan']],
};

export const STORE_EDIT = {
  MASALAH: ['tanggal', 'sesi', 'pemimpin', 'peserta', 'kategori', 'masalah', 'akar', 'solusi', 'pic', 'dueDate', 'prioritas', 'status', 'progress', 'tglSelesai', 'update', 'linkBukti', 'fotoId'],
  CEKLIS: ['status', 'catatan', 'fotoId'], TUGAS: ['status', 'progress', 'tglSelesai', 'catatan', 'fotoId'],
};

export const keys_ = (type) => SCHEMA[type].map((c) => c[0]);
export const tz_ = () => 'Asia/Makassar';
// WITA = UTC+8 tanpa DST; jam diambil dari jam server Supabase
const wita = () => new Date(serverNow() + 8 * 3600000).toISOString();
export const today_ = () => wita().slice(0, 10);
export const now_ = () => { const s = wita(); return s.slice(0, 10) + ' ' + s.slice(11, 16); };
export const hm_ = () => wita().slice(11, 16);
export const stamp_ = () => { const s = wita(); return s.slice(0, 10).replace(/-/g, '') + '_' + s.slice(11, 19).replace(/:/g, ''); };
export function addDays_(s, n) { const p = String(s).split('-'); const d = new Date(Date.UTC(+p[0], +p[1] - 1, +p[2] + n)); return d.toISOString().slice(0, 10); }
export function daysBetween_(a, b) { return Math.round((Date.parse(b + 'T00:00:00Z') - Date.parse(a + 'T00:00:00Z')) / 864e5); }
// isoWeek_ Code.gs dihitung dari tanggal visit (yyyy-mm-dd) agar tidak bergantung zona waktu perangkat
export function isoWeekYmd_(s) {
  const p = String(s).split('-'); const t = new Date(Date.UTC(+p[0], +p[1] - 1, +p[2])); const day = t.getUTCDay() || 7;
  t.setUTCDate(t.getUTCDate() + 4 - day); return Math.ceil((((t - Date.UTC(t.getUTCFullYear(), 0, 1)) / 864e5) + 1) / 7);
}
export function pad_(n, l) { n = String(n); while (n.length < l) n = '0' + n; return n; }
export function parseJ_(s) { if (s && typeof s === 'object') return s; try { return s ? JSON.parse(s) : {}; } catch (e) { return {}; } }
export function fmtTglId_(s) { const p = s.split('-'); return (+p[2]) + ' ' + ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'][+p[1] - 1] + ' ' + p[0]; }
export function parseTglId_(v) {
  if (!v) return '';
  const s = String(v).trim();
  let m = s.match(/^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$/);
  if (m) {
    const b = { jan: 1, feb: 2, mar: 3, apr: 4, mei: 5, may: 5, jun: 6, jul: 7, agu: 8, aug: 8, sep: 9, okt: 10, oct: 10, nov: 11, des: 12, dec: 12 }[m[2].toLowerCase().slice(0, 3)];
    return b ? m[3] + '-' + pad_(b, 2) + '-' + pad_(m[1], 2) : '';
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
  m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/); if (m) return m[1] + '-' + pad_(m[2], 2) + '-' + pad_(m[3], 2);
  m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/); if (m) return m[3] + '-' + pad_(m[2], 2) + '-' + pad_(m[1], 2);   // dd/mm/yyyy (format Indonesia)
  return '';
}
export function mustMgr_(me) { if (!me.isMgr) throw new Error('Hanya SPV Area / Master yang boleh melakukan ini'); }
export function mustMaster_(me) { if (!me.isMaster) throw new Error('Hanya Master yang boleh melakukan ini'); }
export function userSlug_(n) { return n.toLowerCase().replace('tigalapankaos ', 'tk-').replace('mamu ', 'mamu-').replace(/\s+/g, '-'); }
