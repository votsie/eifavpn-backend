import requests
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
import json

# Public endpoints (no auth required)
PUBLIC_PREFIXES = [
    '/system/stats',
]

# Authenticated endpoints (JWT required)
AUTH_PREFIXES = [
    '/users/',
    '/hwid-user-devices/',
    '/nodes',
    '/hosts',
    '/internal-squads',
]

SAFE_PATCH_FIELDS = {'uuid', 'email', 'telegramId', 'description'}


def get_user_from_jwt(request):
    """Extract authenticated user from JWT token."""
    try:
        auth = JWTAuthentication()
        result = auth.authenticate(request)
        if result:
            return result[0]
    except (AuthenticationFailed, Exception):
        pass
    return None


@csrf_exempt
def proxy_view(request, path=''):
    endpoint = f'/{path}'

    # Check if public endpoint
    is_public = any(endpoint.startswith(prefix) for prefix in PUBLIC_PREFIXES)

    # Check if allowed endpoint
    is_allowed = is_public or any(endpoint.startswith(prefix) for prefix in AUTH_PREFIXES)

    if not is_allowed and not (request.method == 'PATCH' and endpoint == '/users'):
        return JsonResponse({'message': 'Endpoint not allowed'}, status=403)

    # Require JWT auth for non-public endpoints
    user = None
    if not is_public:
        user = get_user_from_jwt(request)
        if not user:
            return JsonResponse({'message': 'Authentication required'}, status=401)

        # Ownership check: /users/ endpoints should only access the user's own data
        if endpoint.startswith('/users/') and user.remnawave_uuid:
            user_uuid = str(user.remnawave_uuid)
            # Allow only: /users/{own_uuid}, /users/{own_uuid}/accessible-nodes, /users/by-*
            if not any(endpoint.startswith(p) for p in ['/users/by-', f'/users/{user_uuid}']):
                return JsonResponse({'message': 'Access denied'}, status=403)

    # Filter PATCH /users body — only own UUID
    body = None
    if request.method in ('POST', 'PATCH', 'PUT') and request.body:
        body = json.loads(request.body)
        if request.method == 'PATCH' and endpoint == '/users':
            body = {k: v for k, v in body.items() if k in SAFE_PATCH_FIELDS}
            if 'uuid' not in body:
                return JsonResponse({'message': 'uuid is required'}, status=400)
            # Only allow patching own user
            if user and user.remnawave_uuid and body['uuid'] != str(user.remnawave_uuid):
                return JsonResponse({'message': 'Can only modify own profile'}, status=403)

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
