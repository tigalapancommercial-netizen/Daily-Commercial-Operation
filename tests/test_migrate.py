import csv,importlib.util,pathlib,tempfile,unittest
P=pathlib.Path(__file__).resolve().parents[1]/'scripts'/'migrate_legacy.py'
s=importlib.util.spec_from_file_location('migrator',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_dates_and_aliases(self):
  self.assertEqual(m.date('11 Nov 2026'),'2026-11-11')
  self.assertEqual(m.date('11/11/2026'),'2026-11-11')
  self.assertEqual(m.store_id('tigalapankaos makassar'),'t01')
  self.assertEqual(m.time('09:30'),'09:30:00')
  with self.assertRaises(ValueError):m.store_id('FAKE STORE')
 def test_idempotent_and_fk(self):
  with tempfile.TemporaryDirectory() as d:
   path=pathlib.Path(d)
   with (path/'MASALAH.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['ID','Tanggal Briefing','Toko','Sesi / Jam','Masalah / Temuan','Status','PIC']);w.writeheader();w.writerow({'ID':'MS-0001','Tanggal Briefing':'11 Nov 2026','Toko':'MAMU PALOPO','Sesi / Jam':'Pagi','Masalah / Temuan':'Lampu rusak','Status':'Open','PIC':'GA'})
   runs=[dict((table,rows) for table,rows,_ in m.mapped(path)) for _ in range(2)]
   for run in runs:
    self.assertEqual(len(run['briefings']),1);self.assertEqual(len(run['issues']),1)
    self.assertEqual(run['issues'][0]['briefing_id'],run['briefings'][0]['id'])
   self.assertEqual(runs[0]['issues'][0]['id'],runs[1]['issues'][0]['id'])
   self.assertEqual(runs[0]['issues'][0]['store_id'],'m03')
if __name__=='__main__':unittest.main()
