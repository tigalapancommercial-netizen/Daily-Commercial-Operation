from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from shutil import copyfile
root=Path(__file__).resolve().parents[1]
out=Path('/mnt/data')
patch_paths=[
 'index.html','package.json','package-lock.json',
 'src/main.js','src/db.js','src/xlsx.js',
 'src/server/admin.js','src/server/core.js','src/server/ctx.js',
 'src/server/index.js','src/server/report.js','src/server/util.js',
 'scripts/build_index.py','scripts/patch_v10_photo_nav.py','scripts/patch_v11_compact.py',
 'scripts/patch_v12_before_after.py','scripts/patch_v13_dso_timestamp.py','scripts/patch_v14_assignment_autocheck.py',
 'supabase/migrations/20261113_010_dso_photo_audit.sql',
 'CHANGELOG_v14.md','PANDUAN_PATCH_V14.txt','docs/UPDATE_V14_ASSIGNMENT_AUTO.md'
]
patch=out/'Daily_Commercial_Operation_v14_Patch_Auto_Checklist.zip'
with ZipFile(patch,'w',ZIP_DEFLATED,compresslevel=9) as z:
 for name in patch_paths:
  f=root/name
  assert f.is_file(), f
  z.write(f,arcname=name)
full=out/'Daily_Commercial_Operation_v14_Full_GitHub.zip'
exclude_part={'node_modules','.git','__pycache__','dist','.env','server.log'}
with ZipFile(full,'w',ZIP_DEFLATED,compresslevel=9) as z:
 for f in sorted(root.rglob('*')):
  if not f.is_file() or any(part in exclude_part for part in f.relative_to(root).parts):continue
  rel=f.relative_to(root)
  if f.suffix in {'.pyc','.png','.jpg','.jpeg','.webp','.log'}:continue
  if rel.parts and rel.parts[0]=='preview':continue
  z.write(f,arcname=str(rel))
copyfile(root/'tests/v14_assignment_completed_390.png',out/'DCO_v14_Preview_Assignment_Auto_Check.png')
copyfile(root/'PANDUAN_PATCH_V14.txt',out/'DCO_v14_Panduan_Singkat.txt')
for zip_path in (patch,full):
 with ZipFile(zip_path) as z:
  assert z.testzip() is None
  names=z.namelist()
  assert 'index.html' in names
  assert 'supabase/migrations/20261113_010_dso_photo_audit.sql' in names
  print(zip_path, 'bytes:',zip_path.stat().st_size,'files:',len(names))
