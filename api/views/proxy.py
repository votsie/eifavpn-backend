import requests
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json

ALLOWED_PREFIXES = [
    '/users/by-short-uuid/',
    '/users/by-email/',
    '/users/by-tag/',
    '/users/by-telegram-id/',
    '/users/',
    '/hwid-user-devices/',
    '/nodes',
    '/hosts',
    '/system/stats',
    '/internal-squads',
]

SAFE_PATCH_FIELDS = {'uuid', 'email', 'telegramId', 'description'}


@csrf_exempt
def proxy_view(request, path=''):
    endpoint = f'/{path}'

    # Whitelist check (except PATCH /users which is handled separately)
    if request.method == 'PATCH' and endpoint == '/users':
        pass  # allowed, but body will be filtered
    elif not any(endpoint.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        return JsonResponse({'message': 'Endpoint not allowed'}, status=403)

    # Filter PATCH /users body
    body = None
    if request.method in ('POST', 'PATCH', 'PUT') and request.body:
        body = json.loads(request.body)
        if request.method == 'PATCH' and endpoint == '/users':
            body = {k: v for k, v in body.items() if k in SAFE_PATCH_FIELDS}
            if 'uuid' not in body:
                return JsonResponse({'message': 'uuid is required'}, status=400)

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {settings.REMNAWAVE_BEARER_TOKEN}',
    }

    url = f'{settings.REMNAWAVE_API_URL}{endpoint}'

    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            json=body if body else None,
            timeout=15,
        )
        return HttpResponse(
            resp.content,
            status=resp.status_code,
            content_type='application/json',
        )
    except requests.RequestException as e:
        return JsonResponse({'message': 'Upstream error', 'error': str(e)}, status=502)
