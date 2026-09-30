class SearchEngineIndexingMiddleware:
    """Keep API responses and administration out of search, without blocking reads."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        section = request.path_info.strip('/').split('/', 1)[0]
        if section in {'api', 'admin', 'manager'}:
            # Preserve Django admin's stricter noindex/nofollow header.
            response.setdefault('X-Robots-Tag', 'noindex')
        return response
