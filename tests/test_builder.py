import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'tools' / 'bangun_zip_v26.py'
spec = importlib.util.spec_from_file_location('build_v26', MODULE)
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

BASE_HTML = '<!doctype html><html><head><title>DCO</title></head><body>' + ('<section>Konten menu aplikasi lama tetap utuh.</section>' * 25) + '</body></html>'

class TestV26Builder(unittest.TestCase):
    def test_index_preserves_content_and_injects_once(self):
        patched = b.patch_index(BASE_HTML)
        self.assertIn('Konten menu aplikasi lama tetap utuh.', patched)
        self.assertIn('<script src="./dco-v26-ui-hotfix.js" defer></script>', patched)
        self.assertEqual(b.patch_index(patched).count('dco-v26-ui-hotfix.js'), 1)

    def test_replaces_wrong_absolute_script(self):
        old = BASE_HTML.replace('</body>', '<script src="/dco-v26-ui-hotfix.js" defer></script></body>')
        final = b.patch_index(old)
        self.assertEqual(final.count('dco-v26-ui-hotfix.js'), 1)
        self.assertIn('src="./dco-v26-ui-hotfix.js"', final)

    def test_rejects_incomplete_document(self):
        for invalid in ('<html><body></body>', '<p>hello</p>', 'junk'*100):
            with self.assertRaises(ValueError): b.patch_index(invalid)

    def test_full_zip_keeps_original_files(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            project = t/'app'
            (project/'src').mkdir(parents=True)
            (project/'public').mkdir(parents=True)
            (project/'index.html').write_text(BASE_HTML,encoding='utf-8')
            (project/'src'/'main.js').write_text('console.log("keep main")')
            (project/'src'/'drafts.js').write_text('console.log("keep drafts")')
            (project/'public'/'dco-sw.js').write_text('// SW')
            (project/'package.json').write_text('{}')
            out=t/'built.zip'
            label=b.build(project,out)
            self.assertEqual(label,'SOURCE LENGKAP (struktur terlihat)')
            with zipfile.ZipFile(out) as z:
                self.assertTrue({'index.html','src/main.js','src/drafts.js','public/dco-sw.js','public/dco-v26-ui-hotfix.js','package.json','PANDUAN_V26_HOTFIX.txt'}.issubset(set(z.namelist())))
                self.assertIn('keep drafts',z.read('src/drafts.js').decode())
                self.assertIn('./dco-v26-ui-hotfix.js',z.read('index.html').decode())

    def test_partial_zip_not_mislabelled_full(self):
        with tempfile.TemporaryDirectory() as td:
            t=Path(td)
            src=t/'only-index.zip'
            with zipfile.ZipFile(src,'w') as z:z.writestr('wrapper/index.html',BASE_HTML)
            out=t/'built.zip'
            self.assertEqual(b.build(src,out),'PATCH / SOURCE SEBAGIAN')
            with zipfile.ZipFile(out) as z:
                self.assertIn('index.html',z.namelist())
                self.assertIn('public/dco-v26-ui-hotfix.js',z.namelist())

    def test_zip_slip_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            t=Path(td)
            bad=t/'bad.zip'
            with zipfile.ZipFile(bad,'w') as z:
                z.writestr('../evil.html',BASE_HTML)
                z.writestr('index.html',BASE_HTML)
            with self.assertRaises(ValueError):b.build(bad,t/'out.zip')

if __name__=='__main__':unittest.main(verbosity=2)
