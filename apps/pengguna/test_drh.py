from datetime import date
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import BaseDocTemplate, KeepTogether

from .drh_pdf import BOTTOM, LEFT, RIGHT, STYLES, TOP, WIDTH, _photo, build_drh
from .forms import DrhForm
from .models import Pendidikan, Pelatihan, PesertaPelatihan, Portofolio, RiwayatKarir, Role, User


def story_text(story):
    result = []
    for item in story:
        if hasattr(item, 'getPlainText'):
            result.append(item.getPlainText())
        elif hasattr(item, '_cellvalues'):
            for row in item._cellvalues:
                for cell in row:
                    result.extend(story_text(cell if isinstance(cell, (tuple, list)) else [cell]))
        elif hasattr(item, '_content'):
            result.extend(story_text(item._content))
    return result


class DrhTests(TestCase):
    def setUp(self):
        media = TemporaryDirectory(prefix='drh-tests-')
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.user = User.objects.create_user(
            username='cv-user', first_name='Nadia Contoh, S.T.', nip='123456',
            email='nadia@example.com', no_hp='08123456',
        )
        self.other = User.objects.create_user(username='cv-other', first_name='RAHASIA PENGGUNA LAIN')
        profile = self.user.safe_profile
        profile.tempat_lahir = 'Bandung'
        profile.tanggal_lahir = date(1995, 4, 21)
        profile.jenis_kelamin = 'Perempuan'
        profile.jabatan = 'Analis Laboratorium'
        profile.alamat = 'Jalan Contoh 10'
        profile.save()
        self.education = Pendidikan.objects.create(
            user=self.user, tingkat='Sarjana (S1)', lokasi='Dalam Negeri',
            lembaga='Universitas CV', jurusan='Teknik Kimia', tanggal_lulus=date(2017, 7, 1),
            jenis_nilai='IPK', nilai=3.5,
        )
        self.career = RiwayatKarir.objects.create(
            user=self.user, perusahaan='Instansi CV', jabatan='Analis', status='Karyawan Tetap',
            tanggal_mulai=date(2018, 1, 1), masih_bekerja=True,
            uraian='Pengujian sampel\nPelaporan hasil',
        )
        self.portfolio = Portofolio.objects.create(
            user=self.user, nama='Proyek CV', lokasi='Daerah Contoh', tahun=2026,
            uraian=['Menyusun metode', 'Melaksanakan pengujian'],
        )
        for category, _ in Pelatihan.KATEGORI_CHOICES:
            training = self.training(self.other, category, 'Kegiatan ' + category)
            PesertaPelatihan.objects.create(pelatihan=training, user=self.user)
        self.training(self.user, 'Seminar', 'INPUT TANPA KEIKUTSERTAAN')
        self.training(self.other, 'Seminar', 'PELATIHAN ORANG LAIN')
        Pendidikan.objects.create(
            user=self.other, tingkat='Sarjana (S1)', lokasi='Dalam Negeri',
            lembaga='PENDIDIKAN ORANG LAIN', tanggal_lulus=date(2020, 1, 1), jenis_nilai='IPK', nilai=3,
        )
        Portofolio.objects.create(user=self.other, nama='PROYEK ORANG LAIN', lokasi='Rahasia', tahun=2026)
        self.client.force_login(self.user)
        self.url = reverse('pengguna:drh_download')

    def training(self, user, category, title):
        return Pelatihan.objects.create(
            user=user, kategori_kegiatan=category, nama_pelatihan=title,
            tipe_pelatihan=Pelatihan.TIPE_INTERNAL, jenis_pelatihan=Pelatihan.JENIS_LABORATORIUM,
            tanggal_mulai=date(2025, 6, 1), tanggal_selesai=date(2025, 6, 3), lokasi_pelatihan='Lokasi CV',
        )

    def capture(self, request):
        output = []
        original = BaseDocTemplate.build

        def build(doc, story, **kwargs):
            output.extend(story_text(story))
            return original(doc, story, **kwargs)

        with patch('apps.pengguna.drh_pdf.BaseDocTemplate.build', build):
            response = request()
        return response, output

    def test_hub_shows_header_button_and_four_checked_options(self):
        response = self.client.get(reverse('pengguna:data'))
        self.assertContains(response, 'Generate DRH')
        self.assertContains(response, 'id="drh-modal"')
        self.assertContains(response, 'type="checkbox"', count=4)
        self.assertEqual(response.context['drh_form']['bagian'].value(), [key for key, _ in DrhForm.BAGIAN])

    def test_login_required_and_write_methods_rejected(self):
        self.assertEqual(self.client.post(self.url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_pdf_contains_own_data_in_requested_order_and_training_membership(self):
        response, output = self.capture(lambda: self.client.get(self.url, {
            'bagian': [key for key, _ in reversed(DrhForm.BAGIAN)], 'user': self.other.pk,
        }))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertIn('DRH-nadia-contoh-st.pdf', response['Content-Disposition'])
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertTrue(b''.join(response.streaming_content).startswith(b'%PDF-'))
        for value in ('Nadia Contoh, S.T.', '123456', 'Bandung, 21 Apr 1995', 'Perempuan',
                      'nadia@example.com', '08123456', 'Analis Laboratorium', 'Jalan Contoh 10',
                      'Universitas CV', 'Teknik Kimia', '2017', 'Instansi CV',
                      '2018 - Sekarang', 'Pengujian sampel', 'Pelaporan hasil',
                      'Proyek CV', 'Daerah Contoh', 'Menyusun metode', 'Melaksanakan pengujian',
                      'Hormat saya,'):
            self.assertIn(value, output)
        sections = [f'{chr(65 + index)}. {label}' for index, label in enumerate(
            ['Data Pribadi', *[label for _, label in DrhForm.BAGIAN]],
        )]
        self.assertEqual([output.index(section) for section in sections],
                         sorted(output.index(section) for section in sections))
        categories = [f'{roman}. {value}' for roman, (value, _) in zip(
            ('I', 'II', 'III', 'IV'), Pelatihan.KATEGORI_CHOICES,
        )]
        self.assertEqual([output.index(value) for value in categories], sorted(output.index(value) for value in categories))
        for category, _ in Pelatihan.KATEGORI_CHOICES:
            self.assertIn('Kegiatan ' + category, output)
        self.assertIn('01 Jun 2025 - 03 Jun 2025', output)
        text = '\n'.join(output)
        for hidden in ('INPUT TANPA KEIKUTSERTAAN', 'PELATIHAN ORANG LAIN',
                       'RAHASIA PENGGUNA LAIN', 'PENDIDIKAN ORANG LAIN', 'PROYEK ORANG LAIN'):
            self.assertNotIn(hidden, text)

    def test_each_optional_section_and_personal_only(self):
        for selected in ([], *[[key] for key, _ in DrhForm.BAGIAN]):
            with self.subTest(selected=selected):
                response, output = self.capture(lambda: self.client.get(self.url, {'bagian': selected}))
                self.assertTrue(b''.join(response.streaming_content).startswith(b'%PDF-'))
                self.assertIn('A. Data Pribadi', output)
                self.assertIn('Hormat saya,', output)
                for key, label in DrhForm.BAGIAN:
                    self.assertEqual(f'B. {label}' in output, key in selected)

    def test_unknown_sections_rejected(self):
        self.assertEqual(self.client.get(self.url, {'bagian': ['pendidikan', 'rahasia']}).status_code, 400)

    def test_empty_profile_and_sections_still_generate(self):
        self.client.force_login(self.other)
        response = self.client.get(self.url, {'bagian': [key for key, _ in DrhForm.BAGIAN]})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b''.join(response.streaming_content).startswith(b'%PDF-'))

    def test_missing_profile_still_generates_personal_document(self):
        self.user.safe_profile.delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b''.join(response.streaming_content).startswith(b'%PDF-'))

    def test_finished_career_uses_start_and_end_years(self):
        self.career.masih_bekerja = False
        self.career.tanggal_selesai = date(2023, 12, 31)
        self.career.save()
        response, output = self.capture(lambda: self.client.get(self.url, {'bagian': ['karir']}))
        response.close()
        self.assertIn('2018 - 2023', output)

    def test_photo_and_missing_or_corrupt_photo_do_not_break_pdf(self):
        buffer = BytesIO()
        Image.new('RGB', (100, 180), 'navy').save(buffer, format='PNG')
        profile = self.user.safe_profile
        profile.foto_profil.save('cv.png', SimpleUploadedFile('cv.png', buffer.getvalue()))
        valid_photo = profile.foto_profil.name
        corrupt_photo = profile.foto_profil.storage.save('profile/corrupt.png', SimpleUploadedFile('corrupt.png', b'invalid'))
        for photo in (valid_photo, 'profile/missing.png', corrupt_photo):
            User.objects.filter(pk=self.user.pk).update(first_name='Nadia <CV> & Rekan')
            profile.foto_profil = photo
            profile.save(update_fields=['foto_profil'])
            response = self.client.get(self.url)
            pdf = b''.join(response.streaming_content)
            self.assertTrue(pdf.startswith(b'%PDF-'))
            self.assertEqual(b'/Subtype /Image' in pdf, photo == valid_photo)

    def test_long_points_and_tables_split_across_pages(self):
        self.portfolio.uraian = ['Uraian proyek panjang ' * 600, 'Poin berikutnya']
        self.portfolio.save()
        self.career.uraian = '\n'.join('Uraian karir panjang ' * 30 for _ in range(50))
        self.career.save()
        output = BytesIO()
        build_drh(output, self.user, {'karir', 'portofolio'})
        self.assertTrue(output.getvalue().startswith(b'%PDF-'))
        self.assertGreater(output.getvalue().count(b'/Type /Page'), 3)

    def test_admin_also_exports_only_their_own_records(self):
        role, _ = Role.objects.get_or_create(nama='Super Admin')
        profile = self.user.safe_profile
        profile.role = role
        profile.save(update_fields=['role'])
        response, output = self.capture(lambda: self.client.get(self.url, {'bagian': ['pendidikan', 'portofolio']}))
        self.assertEqual(response.status_code, 200)
        response.close()
        self.assertNotIn('PENDIDIKAN ORANG LAIN', output)
        self.assertNotIn('PROYEK ORANG LAIN', output)

    def test_print_layout_uses_arial_margins_and_column_alignment(self):
        original = BaseDocTemplate.build

        def build(doc, story, **kwargs):
            self.assertEqual((doc.leftMargin, doc.rightMargin, doc.topMargin, doc.bottomMargin),
                             (LEFT, RIGHT, TOP, BOTTOM))
            frame = doc.pageTemplates[0].frames[0]
            self.assertEqual((frame._leftPadding, frame._rightPadding, frame._topPadding, frame._bottomPadding),
                             (0, 0, 0, 0))
            tables = [item for item in story if hasattr(item, '_cellvalues')]
            for table in tables:
                self.assertAlmostEqual(sum(table._argW), WIDTH)
                for header in table._cellvalues[0]:
                    self.assertEqual(header.style.alignment, TA_CENTER)
                    self.assertEqual(header.style.fontName, 'Arial-Bold')
                self.assertEqual(table._cellvalues[1][1].style.fontSize, 11)
            education = next(table for table in tables if table._cellvalues[0][0].getPlainText() == 'Tingkat Pendidikan')
            career = next(table for table in tables if table._cellvalues[0][0].getPlainText() == 'Nama Perusahaan / Instansi')
            training = next(table for table in tables if table._cellvalues[0][0].getPlainText() == 'Nama Kegiatan')
            portfolio = next(table for table in tables if table._cellvalues[0][0].getPlainText() == 'Nama Proyek')
            for table, index in ((education, 4), (career, 3), (training, 1), (portfolio, 3)):
                self.assertEqual(table._cellvalues[1][index].style.alignment, TA_CENTER)
            for table in (training, portfolio):
                self.assertEqual(table._cellvalues[1][0].style.alignment, TA_JUSTIFY)
            for table, index in ((career, 4), (portfolio, 2)):
                for point in table._cellvalues[1][index]:
                    self.assertEqual(point.style.alignment, TA_JUSTIFY)
                    self.assertEqual(point.style.fontName, 'Arial')
                    self.assertEqual(point.style.fontSize, 11)
            personal = tables[0]
            self.assertEqual(personal._spanCmds, [('SPAN', (2, 1), (2, 8))])
            signature = story[-1]
            self.assertIsInstance(signature, KeepTogether)
            self.assertFalse(any(hasattr(item, '_cellvalues') for item in signature._content))
            self.assertGreater(STYLES['sign'].leftIndent, WIDTH / 2)
            return original(doc, story, **kwargs)

        with patch('apps.pengguna.drh_pdf.BaseDocTemplate.build', build):
            build_drh(BytesIO(), self.user, {key for key, _ in DrhForm.BAGIAN})

    def test_signature_uses_current_download_date_in_indonesian(self):
        for day, expected in ((date(2026, 11, 26), 'Bandung, 26 November 2026'),
                              (date(2026, 11, 27), 'Bandung, 27 November 2026')):
            with self.subTest(day=day), patch('apps.pengguna.drh_pdf.timezone.localdate', return_value=day):
                response, output = self.capture(lambda: self.client.get(self.url))
                response.close()
                self.assertIn(expected, output)

    def test_transparent_photo_is_composited_on_white(self):
        picture = Image.new('RGBA', (20, 20), (255, 0, 0, 0))
        picture.putpixel((10, 10), (255, 0, 0, 128))
        buffer = BytesIO()
        picture.save(buffer, format='PNG')
        profile = self.user.safe_profile
        profile.foto_profil.save('transparent.png', SimpleUploadedFile('transparent.png', buffer.getvalue()))
        photo = _photo(profile.foto_profil)
        pixels = photo._img.getRGBData()
        self.assertEqual(pixels[:3], bytes((255, 255, 255)))
        index = (10 * 20 + 10) * 3
        self.assertEqual(pixels[index:index + 3], bytes((255, 127, 127)))

    def test_missing_arial_returns_clear_service_error(self):
        from django.core.exceptions import ImproperlyConfigured
        with patch('apps.pengguna.drh_pdf._fonts', side_effect=ImproperlyConfigured('Font Arial belum tersedia.')):
            response = self.client.get(self.url)
        self.assertContains(response, 'Font Arial untuk DRH belum tersedia pada server.', status_code=503)

    def test_empty_sections_are_locked_unchecked_and_not_exported(self):
        self.user.pendidikan.all().delete()
        self.user.riwayat_karir.all().delete()
        self.user.portofolio.all().delete()
        PesertaPelatihan.objects.filter(user=self.user).delete()
        response = self.client.get(reverse('pengguna:data'))
        form = response.context['drh_form']
        self.assertEqual(form['bagian'].value(), [])
        for option in form['bagian']:
            self.assertTrue(option.data['attrs']['disabled'])
            self.assertNotIn('checked', option.data['attrs'])
        self.assertContains(response, 'Pilih data yang akan dimuat')
        self.assertNotContains(response, 'Data pribadi dan kolom tanda tangan selalu disertakan.')
        self.assertNotContains(response, 'aria-describedby="drh-description"')
        response, output = self.capture(lambda: self.client.get(self.url, {'bagian': [key for key, _ in DrhForm.BAGIAN]}))
        self.assertTrue(b''.join(response.streaming_content).startswith(b'%PDF-'))
        self.assertIn('A. Data Pribadi', output)
        self.assertNotIn('Belum ada data.', output)
        self.assertFalse(any(text.startswith('B. ') for text in output))

    def test_only_empty_category_is_skipped_and_numbering_remains_sequential(self):
        PesertaPelatihan.objects.filter(user=self.user, pelatihan__kategori_kegiatan__in=['Pelatihan', 'Workshop']).delete()
        self.user.riwayat_karir.all().delete()
        self.user.portofolio.all().delete()
        response, output = self.capture(lambda: self.client.get(self.url, {'bagian': [key for key, _ in DrhForm.BAGIAN]}))
        response.close()
        self.assertIn('B. Data Pendidikan', output)
        self.assertIn('C. Data Pelatihan / Diklat / Workshop / Seminar', output)
        self.assertIn('I. Diklat', output)
        self.assertIn('II. Seminar', output)
        self.assertNotIn('III. Seminar', output)
        self.assertNotIn('IV. Workshop', output)
        self.assertNotIn('Kegiatan Pelatihan', output)
        self.assertNotIn('Kegiatan Workshop', output)
        self.assertNotIn('Belum ada data.', output)
        form = self.client.get(reverse('pengguna:data')).context['drh_form']
        self.assertEqual(form.fields['bagian'].widget.locked, {'karir', 'portofolio'})
        self.assertEqual(form['bagian'].value(), ['pendidikan', 'pelatihan'])

    def test_custom_signature_location_and_date_are_used(self):
        for value in ('01 Jun 2027', '2027-06-01'):
            with self.subTest(date=value):
                response, output = self.capture(lambda: self.client.get(self.url, {
                    'lokasi': '  Jakarta  Selatan  ', 'tanggal': value,
                }))
                response.close()
                self.assertIn('Jakarta Selatan, 1 Juni 2027', output)
                self.assertIn('Hormat saya,', output)
                self.assertNotIn('Yang bersangkutan,', output)

    def test_location_and_date_are_required_and_validated_server_side(self):
        for params in ({'lokasi': ''}, {'lokasi': '   '}, {'lokasi': 'x' * 101},
                       {'tanggal': ''}, {'tanggal': '31 Feb 2026'}, {'tanggal': 'invalid'}):
            with self.subTest(params=params):
                self.assertEqual(self.client.get(self.url, params).status_code, 400)
        with patch('apps.pengguna.forms.timezone.localdate', return_value=date(2026, 11, 26)):
            response = self.client.get(reverse('pengguna:data'))
        self.assertContains(response, 'value="Bandung"')
        self.assertContains(response, 'value="26 Nov 2026"')
        self.assertContains(response, 'data-user-date-picker="true"')

    def test_empty_records_are_also_skipped_when_builder_is_called_directly(self):
        self.user.portofolio.all().delete()
        output = []
        original = BaseDocTemplate.build

        def build(doc, story, **kwargs):
            output.extend(story_text(story))
            return original(doc, story, **kwargs)

        with patch('apps.pengguna.drh_pdf.BaseDocTemplate.build', build):
            build_drh(BytesIO(), self.user, {'portofolio'})
        self.assertNotIn('B. Portofolio Proyek & Kegiatan', output)
        self.assertNotIn('Nama Proyek', output)
