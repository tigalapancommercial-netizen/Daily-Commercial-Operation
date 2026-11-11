-- Supabase Dashboard > SQL Editor. Ubah email sebelum menjalankan.
-- Menampilkan apakah email ada di Auth serta apakah profil sudah tersedia.
select
  u.email,
  u.id as auth_user_id,
  (u.email_confirmed_at is not null) as email_terkonfirmasi,
  p.id is not null as profil_terdaftar,
  p.display_name,
  p.role,
  p.store_id,
  p.active
from auth.users u
left join public.profiles p on p.id=u.id
where lower(u.email)=lower(trim('GANTI_EMAIL_LOGIN_ANDA'));

-- Jika hasil 0 baris, buat akun dulu melalui Authentication > Users.
-- Jika profil_terdaftar=false, jalankan 01_BUAT_PROFIL_MASTER.sql
-- Jika p ada namun aplikasi tetap tidak bisa membaca, periksa kebijakan RLS:
select schemaname, tablename, policyname, cmd, roles
from pg_policies
where schemaname='public' and tablename='profiles';
