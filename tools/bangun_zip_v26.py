#!/usr/bin/env python3
"""Create a real, combined v26 DCO ZIP from a supplied original source folder/ZIP.

Does not invent or replace missing application source files. Pure stdlib.
Usage: python bangun_zip_v26.py <source_folder_or_zip> [output.zip]
"""
from __future__ import annotations

import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
JS_FILE = HERE / "public" / "dco-v26-ui-hotfix.js"
TAG = '<script src="./dco-v26-ui-hotfix.js" defer></script>'
OLD_JS_RE = re.compile(r"\s*<script\b(?=[^>]*\bsrc\s*=\s*['\"](?:/|\./)?dco-v26-ui-hotfix\.js['\"])[^>]*>\s*</script>\s*", re.I)
BODY_CLOSE_RE = re.compile(r"</body\s*>", re.I)


def patch_index(original: str) -> str:
    if not re.search(r"<!doctype\s+html\b|<html\b", original, re.I):
        raise ValueError("Bukan dokumen HTML utuh: tidak ada DOCTYPE atau <html>.")
    if not BODY_CLOSE_RE.search(original):
        raise ValueError("Dokumen HTML tidak memiliki </body>; tidak diubah demi keamanan.")
    if len(original) < 350:
        raise ValueError("index.html terlalu pendek; kemungkinan file kosong / placeholder.")
    cleaned = OLD_JS_RE.sub("\n", original)
    # Insert before the final closing body in case script tags exist inside samples.
    matches = list(BODY_CLOSE_RE.finditer(cleaned))
    match = matches[-1]
    return cleaned[:match.start()] + "  " + TAG + "\n" + cleaned[match.start():]


def extract_safe(zf: zipfile.ZipFile, target: Path) -> None:
    for info in zf.infolist():
        if info.is_dir():
            continue
        name = info.filename.replace('\\', '/')
        parts = Path(name).parts
        if Path(name).is_absolute() or '..' in parts or not parts or ':' in parts[0]:
            raise ValueError(f"Arsip mengandung path tidak aman: {name}")
        if name.startswith('__MACOSX/') or Path(name).name == '.DS_Store':
            continue
        dst = target.joinpath(*parts)
        dst.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info, 'r') as src, dst.open('wb') as out:
            shutil.copyfileobj(src, out)


def find_project_root(root: Path) -> Path:
    candidates = [p.parent for p in root.rglob('index.html') if p.is_file()]
    if not candidates:
        raise ValueError("index.html tidak ditemukan pada source asli.")
    # Exclude archive tooling folders, mock previews, and HTML test fixtures.
    candidates = [p for p in candidates if not any(x in ('tests', 'examples', 'contoh', 'preview') for x in p.relative_to(root).parts)]
    if not candidates:
        raise ValueError("Hanya index.html contoh/test yang ditemukan, bukan aplikasi asli.")
    def rank(p: Path) -> tuple[int, int, int]:
        return (int((p/'src'/'main.js').is_file()), int((p/'package.json').is_file()), -len(p.parts))
    candidates.sort(key=rank, reverse=True)
    if len(candidates)>1 and rank(candidates[0])==rank(candidates[1]):
        raise ValueError("Ada beberapa index.html kandidat. Pilih folder aplikasi aslinya secara langsung.")
    return candidates[0]


def build(source: Path, output: Path) -> str:
    if not source.exists():
        raise FileNotFoundError(f"Source tidak ada: {source}")
    with tempfile.TemporaryDirectory(prefix='dco_v26_') as td:
        work = Path(td)
        raw = work / 'raw'
        raw.mkdir()
        if source.is_dir():
            shutil.copytree(source, raw, dirs_exist_ok=True)
        elif source.suffix.lower() == '.zip':
            with zipfile.ZipFile(source) as zf:
                extract_safe(zf, raw)
        else:
            raise ValueError("Source harus berupa folder project atau ZIP source asli.")
        project = find_project_root(raw)
        index_file = project / 'index.html'
        original = index_file.read_text(encoding='utf-8-sig')
        new = patch_index(original)
        index_file.write_text(new, encoding='utf-8')
        dest_js = project / 'public' / JS_FILE.name
        dest_js.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(JS_FILE, dest_js)
        complete = (project/'package.json').is_file() and (project/'src'/'main.js').is_file()
        label = 'SOURCE LENGKAP (struktur terlihat)' if complete else 'PATCH / SOURCE SEBAGIAN'
        doc = f'''TIGALAPAN DCO v26 UI - HASIL PENGGABUNGAN\n\nJenis sumber: {label}.\nBerisi seluruh file pada sumber masukan, bukan kode aplikasi buatan ulang.\n\nPerubahan:\n- index.html: menambahkan script relatif ./dco-v26-ui-hotfix.js\n- public/dco-v26-ui-hotfix.js: pembenahan sidebar + sembunyikan panel Draft/Foto\n\nKETERBATASAN PENTING:\n- Perbaikan ini hanya tampilan. Tidak menjamin pemulihan draft otomatis.\n- Pada v25 pemulihan draft masih perlu tombol Draft/Pulihkan manual.\n- Panel tersembunyi bisa dibuka sementara Ctrl+Alt+D.\n- DILARANG mengganti seluruh repository dengan ZIP jika sumber adalah PATCH / SOURCE SEBAGIAN.\n- Backup lebih dulu; periksa hasil build dan uji pemulihan draft sebelum deploy.\n- Jangan menghapus, mereset atau membersihkan storage browser saat draft belum disinkron.\n\nFile asli index.html tidak dibuat dari nol agar semua menu/fitur dipertahankan.\n'''
        (project/'PANDUAN_V26_HOTFIX.txt').write_text(doc, encoding='utf-8')
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
            for p in sorted(project.rglob('*')):
                if p.is_file() and p.resolve()!=output.resolve():
                    z.write(p, p.relative_to(project).as_posix())
        return label


def main() -> None:
    if len(sys.argv) not in (2, 3):
        raise SystemExit('Pakai: python bangun_zip_v26.py SOURCE.zip [HASIL.zip]')
    src = Path(sys.argv[1]).expanduser().resolve()
    out = Path(sys.argv[2]).expanduser().resolve() if len(sys.argv)==3 else Path.cwd()/'Tigalapan_DCO_v26_GABUNGAN.zip'
    try:
        label=build(src,out)
    except (OSError, ValueError, zipfile.BadZipFile) as e:
        print(f'GAGAL: {e}',file=sys.stderr)
        raise SystemExit(2)
    print(f'BERHASIL: {out}\nJenis sumber: {label}\nPenting: pastikan auto-restore draft telah diuji sebelum digunakan produksi.')

if __name__ == '__main__':
    main()
