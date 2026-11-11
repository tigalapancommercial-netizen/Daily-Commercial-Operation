-- KHUSUS AKUN MASTER YANG SAH. Jalankan di Supabase SQL Editor sebagai administrator.
-- PENTING: GANTI email berikut dengan email yang dipakai login di website.
-- Perintah ini membuat/menetapkan role MASTER hanya untuk 1 akun yang dipilih.
DO $$
DECLARE
  login_email text := 'GANTI_EMAIL_LOGIN_ANDA';
  user_uuid uuid;
BEGIN
  IF lower(trim(login_email)) = lower('GANTI_EMAIL_LOGIN_ANDA') OR strpos(login_email,'@')=0 THEN
    RAISE EXCEPTION 'Ganti GANTI_EMAIL_LOGIN_ANDA dengan email akun Master yang sebenarnya.';
  END IF;

  SELECT id INTO user_uuid
  FROM auth.users
  WHERE lower(email)=lower(trim(login_email));

  IF user_uuid IS NULL THEN
    RAISE EXCEPTION 'Email % belum terdaftar di Supabase Authentication > Users.', login_email;
  END IF;

  INSERT INTO public.profiles (id,display_name,role,store_id,active)
  VALUES (user_uuid, 'Master Tigalapan', 'master', NULL, true)
  ON CONFLICT (id) DO UPDATE
  SET display_name=EXCLUDED.display_name,
      role=EXCLUDED.role,
      store_id=NULL,
      active=true;
  RAISE NOTICE 'Profil Master tersedia dan aktif untuk akun % (ID: %)', login_email, user_uuid;
END $$;

-- Untuk cek ulang, jalankan 00_PERIKSA_AKUN.sql dengan email yang sama.
