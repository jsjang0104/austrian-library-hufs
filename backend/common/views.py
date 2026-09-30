from django.http import HttpResponse
from django.views.decorators.http import require_safe


@require_safe
def robots_txt(request):
    # Public notices/books and their rendering resources remain crawlable.
    # Prefixes also cover the slashless URLs that Django redirects.
    rules = (
        'User-agent: *\n'
        'Disallow: /admin\n'
        'Disallow: /manager\n'
        'Disallow: /api/members\n'
        'Disallow: /api/loans\n'
        'Disallow: /api/token\n'
        'Disallow: /api/books/smart_search\n'
    )
    return HttpResponse(rules, content_type='text/plain; charset=utf-8')
