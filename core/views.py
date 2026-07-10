"""Compatibilidade das views do core.

As URLs antigas importam `core.views`. A implementa??o foi separada em
m?dulos por dom?nio para reduzir o tamanho do arquivo e facilitar evolu??o.
"""

from .view_modules.common import *  # noqa: F401,F403
from .view_modules.auth import *  # noqa: F401,F403
from .view_modules.portal import *  # noqa: F401,F403
from .view_modules.mv import *  # noqa: F401,F403
from .view_modules.status import *  # noqa: F401,F403
from .view_modules.manuais import *  # noqa: F401,F403
from .view_modules.links import *  # noqa: F401,F403
from .view_modules.notifications import *  # noqa: F401,F403
from .view_modules.favorites import *  # noqa: F401,F403
