from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme


def get_next_url(request):
    next_url = str(request.POST.get("next") or request.GET.get("next") or "").strip()
    if not next_url:
        return ""

    allowed_hosts = {request.get_host()}
    if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts=allowed_hosts,
        require_https=request.is_secure(),
    ):
        return next_url
    return ""


def redirect_next(request, to, *args, **kwargs):
    next_url = get_next_url(request)
    if next_url:
        return redirect(next_url)
    return redirect(to, *args, **kwargs)
