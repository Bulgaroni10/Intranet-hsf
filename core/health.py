import logging

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


logger = logging.getLogger(__name__)


@never_cache
@require_GET
def healthcheck(request):
    """Verifica se a aplicação consegue atender e consultar o banco principal."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        logger.exception('Healthcheck detectou indisponibilidade do banco principal.')
        return JsonResponse({'status': 'unavailable', 'database': 'error'}, status=503)

    return JsonResponse({'status': 'ok', 'database': 'ok'})
