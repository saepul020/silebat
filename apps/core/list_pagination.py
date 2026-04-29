from django.core.paginator import Paginator

LIST_ENTRY_OPTIONS = ("10", "25", "50", "100", "all")
LIST_DEFAULT_ENTRIES = "10"


def normalize_entries(value):
    raw_value = str(value or LIST_DEFAULT_ENTRIES).strip().lower()
    if raw_value in LIST_ENTRY_OPTIONS:
        return raw_value
    return LIST_DEFAULT_ENTRIES


def _count_items(items):
    try:
        return items.count()
    except TypeError:
        return len(items)
    except AttributeError:
        return len(items)


def paginate_list(request, queryset, *, entries_param="entries", page_param="page"):
    selected_entries = normalize_entries(request.GET.get(entries_param))
    total_count = _count_items(queryset)

    query_params = request.GET.copy()
    query_params.pop(entries_param, None)
    query_params.pop(page_param, None)
    base_query = query_params.urlencode()

    pagination_context = {
        "selected_entries": selected_entries,
        "has_entries_filter": bool(request.GET.get(entries_param)),
        "entry_options": LIST_ENTRY_OPTIONS,
        "total_count": total_count,
        "start_index": 0,
        "end_index": 0,
        "page_obj": None,
        "is_paginated": False,
        "page_range": [],
        "show_all_entries": False,
        "pagination_base_query": f"{base_query}&" if base_query else "",
    }

    if selected_entries == "all":
        pagination_context.update(
            {
                "items": queryset,
                "start_index": 1 if total_count else 0,
                "end_index": total_count,
                "show_all_entries": True,
            }
        )
        return pagination_context

    paginator = Paginator(queryset, int(selected_entries))
    page_obj = paginator.get_page(request.GET.get(page_param, 1))
    if hasattr(paginator, "get_elided_page_range"):
        page_range = paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1)
    else:
        page_range = paginator.page_range

    pagination_context.update(
        {
            "items": page_obj.object_list,
            "page_obj": page_obj,
            "is_paginated": page_obj.has_other_pages(),
            "page_range": page_range,
            "start_index": page_obj.start_index() if total_count else 0,
            "end_index": page_obj.end_index() if total_count else 0,
        }
    )
    return pagination_context
