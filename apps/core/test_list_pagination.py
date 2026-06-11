from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase

from apps.pengguna.models import User

from apps.core.list_pagination import LIST_SEARCH_MAX_LENGTH, paginate_list


class ListPaginationSearchTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        User.objects.create_user(username="alpha", email="alpha@example.com")
        User.objects.create_user(username="target-user", email="target@example.com")

    def test_search_filters_before_pagination(self):
        request = self.factory.get("/users/", {"q": " target ", "entries": "10"})

        context = paginate_list(
            request,
            User.objects.order_by("username"),
            search_fields=("username", "email"),
        )

        self.assertEqual(context["search_query"], "target")
        self.assertEqual(context["total_count"], 1)
        self.assertEqual(list(context["items"])[0].username, "target-user")

    def test_search_is_limited_and_preserves_other_filters(self):
        raw_query = "x" * (LIST_SEARCH_MAX_LENGTH + 20)
        request = self.factory.get(
            "/users/",
            {"q": raw_query, "entries": "25", "status": "aktif", "page": "2"},
        )

        context = paginate_list(
            request,
            User.objects.order_by("username"),
            search_fields=("username",),
        )

        self.assertEqual(len(context["search_query"]), LIST_SEARCH_MAX_LENGTH)
        self.assertEqual(context["list_filter_params"], [("status", "aktif")])
        self.assertNotIn("page=", context["pagination_base_query"])

    def test_report_search_control_follows_year_without_submit_button(self):
        html = render_to_string(
            "components/entry_control.html",
            {
                "selected_entries": "10",
                "has_entries_filter": False,
                "search_query": "",
                "search_max_length": LIST_SEARCH_MAX_LENGTH,
                "has_search": False,
                "list_filter_params": [],
                "total_count": 0,
                "show_report_year_filter": True,
            },
        )

        self.assertLess(html.index("masterEntriesSelect"), html.index("reportYearSelect"))
        self.assertLess(html.index("reportYearSelect"), html.index("data-master-search"))
        self.assertIn(f'maxlength="{LIST_SEARCH_MAX_LENGTH}"', html)
        self.assertNotIn("master-list-search-submit", html)
