from datetime import date

from django.db import connection
from django.template.loader import render_to_string
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.dashboard.views import build_active_context, get_active_peminjaman_queryset
from apps.operasional.models import TIM_LAYANAN_TEKNIS_NAME, TimKegiatan
from apps.pemeliharaan.models import (
    ACTIVE_PEMELIHARAAN_STEPS,
    KondisiPemeliharaanChoices,
    MetodePerbaikanChoices,
    PemeliharaanItem,
    PemeliharaanPengajuan,
    StepPemeliharaanChoices,
    TindakanPerbaikanChoices,
)
from apps.peminjaman.models import PeminjamanRequest, ReturnStepChoices, StepChoices
from apps.pengguna.models import Role, User


class DashboardActiveTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = {}
        for key, role_name in (
            ("admin", "Admin Lab"),
            ("other_admin", "Admin Lab"),
            ("super", "Super Admin"),
            ("kepala", "Kepala Lab"),
            ("pimpinan", "Pimpinan"),
            ("other_pimpinan", "Pimpinan"),
            ("teknisi", "Teknisi Lab"),
            ("user", "User"),
        ):
            role, _ = Role.objects.get_or_create(nama=role_name)
            user = User.objects.create_user(username=f"dashboard-active-{key}")
            user.safe_profile.role = role
            user.safe_profile.save(update_fields=["role"])
            cls.users[key] = user
        cls.users["no_role"] = User.objects.create_user(username="dashboard-active-no-role")
        cls.tim, _ = TimKegiatan.objects.update_or_create(
            nama_tim=TIM_LAYANAN_TEKNIS_NAME,
            defaults={"ketua_tim": cls.users["pimpinan"]},
        )
        cls.maintenance = {}
        for step in StepPemeliharaanChoices:
            obj = PemeliharaanPengajuan.objects.create(
                pemohon=cls.users["admin"],
                current_step=step,
                metode_perbaikan=MetodePerbaikanChoices.MANDIRI if step == StepPemeliharaanChoices.PERBAIKAN_MANDIRI else MetodePerbaikanChoices.EKSTERNAL,
                snapshot_nama_barang=f"Alat {step}",
            )
            PemeliharaanItem.objects.create(
                pengajuan=obj,
                komponen="Sensor",
                kondisi=KondisiPemeliharaanChoices.PERLU_PERBAIKAN,
                tindakan_perbaikan=TindakanPerbaikanChoices.LANJUTAN,
            )
            cls.maintenance[step] = obj

    def active_context(self, user_key):
        loans = get_active_peminjaman_queryset()
        context = build_active_context(self.users[user_key], loans)
        return context["active_pemeliharaan"], loans

    def create_loan(self, step=StepChoices.ADMIN_LAB, return_step=ReturnStepChoices.NONE):
        return PeminjamanRequest.objects.create(
            peminjam=self.users["user"],
            nama_peminjam="Peminjam Dashboard",
            tanggal_mulai=date(2026, 11, 18),
            tanggal_selesai=date(2026, 11, 19),
            current_step=step,
            return_current_step=return_step,
            tim_kegiatan=self.tim,
        )

    def test_all_active_maintenance_steps_include_drafts_and_exclude_final_steps(self):
        items, _ = self.active_context("admin")

        self.assertEqual({item.current_step for item in items}, set(ACTIVE_PEMELIHARAAN_STEPS))

    def test_maintenance_visible_to_all_users_regardless_of_role_or_owner(self):
        own = PemeliharaanPengajuan.objects.create(pemohon=self.users["user"])
        expected_ids = {
            item.pk for step, item in self.maintenance.items()
            if step in ACTIVE_PEMELIHARAAN_STEPS
        } | {own.pk}
        for role, user in self.users.items():
            with self.subTest(role=role):
                self.client.force_login(user)
                response = self.client.get(reverse("dashboard:index"))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    {item.pk for item in response.context["active_pemeliharaan"]},
                    expected_ids,
                )
                for step, item in self.maintenance.items():
                    if step in ACTIVE_PEMELIHARAAN_STEPS:
                        self.assertContains(response, item.nomor_pengajuan)
                    else:
                        self.assertNotContains(response, item.nomor_pengajuan)

    def test_maintenance_actions_follow_stage_and_actor(self):
        for role, step, route in (
            ("admin", StepPemeliharaanChoices.DRAFT, "pemeliharaan:list"),
            ("admin", StepPemeliharaanChoices.DIKEMBALIKAN, "pemeliharaan:list"),
            ("admin", StepPemeliharaanChoices.VENDOR_DRAFT, "pemeliharaan:list"),
            ("admin", StepPemeliharaanChoices.PERBAIKAN_MANDIRI, "pemeliharaan:list"),
            ("kepala", StepPemeliharaanChoices.KEPALA_LAB, "verifikasi:index"),
            ("kepala", StepPemeliharaanChoices.VENDOR_KEPALA_LAB, "verifikasi:index"),
            ("pimpinan", StepPemeliharaanChoices.PIMPINAN, "verifikasi:index"),
            ("pimpinan", StepPemeliharaanChoices.VENDOR_PIMPINAN, "verifikasi:index"),
        ):
            with self.subTest(role=role, step=step):
                items, _ = self.active_context(role)
                item = next(item for item in items if item.current_step == step)
                self.assertEqual(item.action_url, reverse(route))
                self.client.force_login(self.users[role])
                self.assertEqual(self.client.get(item.action_url).status_code, 200)

    def test_other_actors_cannot_follow_up_maintenance(self):
        for role, step, route in (
            ("other_admin", StepPemeliharaanChoices.DRAFT, "pemeliharaan:edit"),
            ("other_admin", StepPemeliharaanChoices.VENDOR_DRAFT, "pemeliharaan:vendor"),
            ("admin", StepPemeliharaanChoices.KEPALA_LAB, "verifikasi:detail_pemeliharaan"),
            ("kepala", StepPemeliharaanChoices.PIMPINAN, "verifikasi:detail_pemeliharaan"),
            ("other_pimpinan", StepPemeliharaanChoices.PIMPINAN, "verifikasi:detail_pemeliharaan"),
            ("user", StepPemeliharaanChoices.DRAFT, "pemeliharaan:edit"),
            ("user", StepPemeliharaanChoices.KEPALA_LAB, "verifikasi:detail_pemeliharaan"),
            ("no_role", StepPemeliharaanChoices.DRAFT, "pemeliharaan:edit"),
        ):
            with self.subTest(role=role, step=step):
                items, _ = self.active_context(role)
                item = next(item for item in items if item.current_step == step)
                self.assertEqual(item.action_url, "")
                self.client.force_login(self.users[role])
                self.assertRedirects(
                    self.client.get(reverse(route, args=[item.pk])),
                    reverse("dashboard:index"),
                    fetch_redirect_response=False,
                )

    def test_super_admin_can_follow_up_every_active_maintenance_step(self):
        items, _ = self.active_context("super")
        self.assertTrue(all(item.action_url for item in items))

    def test_loan_actions_route_to_verification_menu(self):
        for role, step, return_step in (
            ("admin", StepChoices.ADMIN_LAB, ReturnStepChoices.NONE),
            ("teknisi", StepChoices.TEKNISI_LAB, ReturnStepChoices.NONE),
            ("kepala", StepChoices.KEPALA_LAB, ReturnStepChoices.NONE),
            ("pimpinan", StepChoices.PIMPINAN, ReturnStepChoices.NONE),
            ("user", StepChoices.APPROVED, ReturnStepChoices.USER_VERIFICATION),
            ("teknisi", StepChoices.APPROVED, ReturnStepChoices.TEKNISI_BA),
            ("pimpinan", StepChoices.APPROVED, ReturnStepChoices.PIMPINAN_TRANSFER),
        ):
            with self.subTest(role=role, step=step, return_step=return_step):
                obj = self.create_loan(step, return_step)
                _, items = self.active_context(role)
                item = next(item for item in items if item.pk == obj.pk)
                self.assertEqual(item.action_url, reverse("verifikasi:index"))
                self.client.force_login(self.users[role])
                self.assertEqual(self.client.get(item.action_url).status_code, 200)

    def test_loan_actions_absent_outside_users_turn(self):
        for role, step, return_step in (
            ("user", StepChoices.ADMIN_LAB, ReturnStepChoices.NONE),
            ("kepala", StepChoices.APPROVED, ReturnStepChoices.NONE),
            ("user", StepChoices.APPROVED, ReturnStepChoices.NONE),
            ("admin", StepChoices.APPROVED, ReturnStepChoices.NONE),
            ("super", StepChoices.APPROVED, ReturnStepChoices.NONE),
            ("other_pimpinan", StepChoices.PIMPINAN, ReturnStepChoices.NONE),
            ("admin", StepChoices.APPROVED, ReturnStepChoices.USER_VERIFICATION),
        ):
            with self.subTest(role=role, step=step, return_step=return_step):
                obj = self.create_loan(step, return_step)
                _, items = self.active_context(role)
                self.assertEqual(next(item for item in items if item.pk == obj.pk).action_url, "")

    def test_dashboard_table_order_icon_actions_and_existing_modal(self):
        loan = self.create_loan()
        self.client.force_login(self.users["admin"])

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)
        markup = response.content.decode()
        self.assertLess(markup.index("Data Kegiatan Aktif"), markup.index("Data Pemeliharaan Aktif"))
        self.assertContains(response, '<th class="cell-action">Aksi</th>', count=2)
        self.assertNotContains(response, '<th class="cell-action">Detail Barang</th>')
        self.assertNotContains(response, "<span>Detail</span>")
        self.assertContains(response, f'data-item-open="itemModal{loan.pk}"')
        self.assertContains(response, f'id="itemModal{loan.pk}"')
        self.assertContains(response, 'aria-label="Cari pemeliharaan aktif"')
        self.assertContains(response, 'class="btn btn-primary btn-sm"', count=5)
        self.assertNotContains(response, 'disabled title="Menunggu giliran tindak lanjut"')
        self.assertContains(response, 'title="Buka menu Verifikasi %s"' % loan.nomor_pengajuan)
        for step, item in self.maintenance.items():
            if step in ACTIVE_PEMELIHARAAN_STEPS:
                self.assertContains(response, item.nomor_pengajuan)
            else:
                self.assertNotContains(response, item.nomor_pengajuan)

    def test_followup_markup_only_exists_for_authorized_actions(self):
        for role in self.users:
            items, _ = self.active_context(role)
            for item in items:
                with self.subTest(role=role, step=item.current_step):
                    markup = render_to_string("dashboard/partials/followup_button.html", {"item": item})
                    if item.action_url:
                        self.assertIn(f'href="{item.action_url}"', markup)
                        self.assertIn('class="btn btn-primary btn-sm"', markup)
                        self.assertNotIn("disabled", markup)
                    else:
                        self.assertEqual(markup.strip(), "")

    def test_dashboard_hides_followup_buttons_for_user_without_pending_actions(self):
        self.create_loan()
        own = PemeliharaanPengajuan.objects.create(pemohon=self.users["user"])
        self.client.force_login(self.users["user"])

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'class="btn btn-primary btn-sm"')
        self.assertContains(response, reverse("pemeliharaan:detail", args=[own.pk]))
        self.assertContains(response, 'class="bi bi-eye-fill"')
        self.assertContains(response, self.maintenance[StepPemeliharaanChoices.DRAFT].nomor_pengajuan)

    def test_empty_table_and_login_requirement(self):
        self.assertRedirects(
            self.client.get(reverse("dashboard:index")),
            reverse("login") + "?next=" + reverse("dashboard:index"),
        )
        PemeliharaanPengajuan.objects.filter(current_step__in=ACTIVE_PEMELIHARAAN_STEPS).delete()
        self.client.force_login(self.users["user"])
        response = self.client.get(reverse("dashboard:index"))
        self.assertContains(response, "Belum ada data pemeliharaan aktif.")

    def test_maintenance_rows_do_not_add_queries_per_row(self):
        def query_count():
            with CaptureQueriesContext(connection) as queries:
                items, _ = self.active_context("admin")
                for item in items:
                    (item.nama_pelaksana, item.alat_label, item.perlu_perbaikan)
            return len(queries)

        initial_count = query_count()
        for _ in range(4):
            PemeliharaanPengajuan.objects.create(pemohon=self.users["admin"])
        self.assertEqual(query_count(), initial_count)
