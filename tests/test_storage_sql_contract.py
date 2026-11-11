from pathlib import Path
import unittest
SQL=(Path(__file__).resolve().parents[1]/'supabase/migrations/20261111_005_storage_maintenance.sql').read_text()
class Contract(unittest.TestCase):
 def test_master_gate_and_restrictions(self):
  for term in ["private.role_name() is distinct from 'master'",'minimal 90 hari','p_expected is distinct from n','copied<>n','deleted<>n','24 hours',"'HAPUS ARSIP PERMANEN'",'private.maintenance_rows']:
   with self.subTest(term=term):self.assertIn(term,SQL)
 def test_no_automatic_deletion(self):
  self.assertNotIn('truncate table public.',SQL.lower())
  self.assertNotIn('drop table public.',SQL.lower())
  self.assertNotIn('delete from storage.objects',SQL.lower())
 def test_protected_parent_tables(self):
  allowed=SQL.split("if p_table not in (")[1].split(')')[0]
  for protected in ['visits','visit_points','briefings','profiles','audit_events']:
   self.assertNotIn("'"+protected+"'",allowed)
 def test_sql_dollar_quotes_balanced(self):
  self.assertEqual(SQL.count('$$')%2,0)
if __name__=='__main__':unittest.main()
