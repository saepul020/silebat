import re
from datetime import date

from django.test import TestCase
from django.urls import reverse

from .models import Role, User
from .forms import UserProfileForm


class DataPenggunaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='data-user')
        cls.other = User.objects.create_user(username='data-other')
        cls.admin = User.objects.create_user(username='data-admin')
        role, _ = Role.objects.get_or_create(nama='Super Admin')
        profile = cls.admin.safe_profile
        profile.role = role
        profile.save(update_fields=['role'])

    def test_hub_requires_login(self):
        response = self.client.get(reverse('pengguna:data'))
        self.assertRedirects(response, '/login/?next=/pengguna/data/', fetch_redirect_response=False)

    def test_personal_fields_save_and_restore_on_edit_and_detail(self):
        self.client.force_login(self.user)
        url = reverse('pengguna:edit', args=[self.user.pk])
        response = self.client.post(url, {
            'nama_lengkap': 'Pengguna Contoh', 'email': 'contoh@example.com',
            'tempat_lahir': 'Bandung', 'tanggal_lahir': '29 Feb 2000', 'jenis_kelamin': 'Perempuan',
        })
        self.assertRedirects(response, reverse('pengguna:detail', args=[self.user.pk]))
        profile = self.user.safe_profile
        profile.refresh_from_db()
        self.assertEqual(profile.tempat_lahir, 'Bandung')
        self.assertEqual(profile.tanggal_lahir, date(2000, 2, 29))
        self.assertEqual(profile.jenis_kelamin, 'Perempuan')
        response = self.client.get(url)
        self.assertContains(response, 'value="29 Feb 2000"')
        self.assertContains(response, 'data-user-date-picker="true"')
        self.assertEqual(response.context['form_profile']['jenis_kelamin'].value(), 'Perempuan')
        detail = self.client.get(reverse('pengguna:detail', args=[self.user.pk]))
        for text in ('Bandung', 'Perempuan', '29 Feb 2000'):
            self.assertContains(detail, text)

    def test_personal_fields_reject_invalid_values_and_allow_empty_legacy_profiles(self):
        for changes, field in (
            ({'tanggal_lahir': '31 Feb 2000'}, 'tanggal_lahir'),
            ({'jenis_kelamin': 'Tidak valid'}, 'jenis_kelamin'),
            ({'tempat_lahir': 'x' * 101}, 'tempat_lahir'),
        ):
            form = UserProfileForm(changes, instance=self.user.safe_profile)
            self.assertFalse(form.is_valid())
            self.assertIn(field, form.errors)
        for gender in ('Laki-Laki', 'Perempuan'):
            form = UserProfileForm({'tanggal_lahir': '2000-02-29', 'jenis_kelamin': gender}, instance=self.user.safe_profile)
            self.assertTrue(form.is_valid(), form.errors)
        form = UserProfileForm({}, instance=self.user.safe_profile)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data['tanggal_lahir'])

    def test_hub_links_to_own_profile_for_user_and_admin(self):
        for actor in (self.user, self.admin):
            with self.subTest(actor=actor.username):
                self.client.force_login(actor)
                response = self.client.get(reverse('pengguna:data'))
                self.assertContains(response, 'class="user-menu__card"', count=5)
                self.assertContains(response, f'href="{reverse("pengguna:detail", args=[actor.pk])}" class="user-menu__card"')
                self.assertContains(response, f'href="{reverse("pengguna:pelatihan_daftar")}" class="user-menu__card"')
                sidebar = response.content.decode().split('<nav class="sidebar-nav">')[1].split('</nav>')[0]
                self.assertNotIn('>Data Pelatihan</a>', sidebar)
                self.assertEqual('>Daftar Pengguna</a>' in sidebar, actor == self.admin)

    def test_child_pages_keep_data_pengguna_active_and_return_to_hub(self):
        self.client.force_login(self.user)
        for url in (reverse('pengguna:detail', args=[self.user.pk]), reverse('pengguna:pelatihan_daftar')):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'aria-current="page">Data Pengguna</a>')
                self.assertRegex(response.content.decode(), rf'href="{re.escape(reverse("pengguna:data"))}" class="btn btn-secondary"')
        self.assertContains(self.client.get(reverse('pengguna:detail', args=[self.user.pk])), '<h1>Data Pribadi</h1>')

    def test_profile_permissions_and_admin_return_are_preserved(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse('pengguna:detail', args=[self.other.pk])), reverse('dashboard:index'), fetch_redirect_response=False)
        self.client.force_login(self.admin)
        response = self.client.get(reverse('pengguna:detail', args=[self.other.pk]))
        self.assertContains(response, f'href="{reverse("pengguna:daftar")}" class="btn btn-secondary">Kembali</a>')
