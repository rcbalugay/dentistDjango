import logging
from django.db import DEFAULT_DB_ALIAS

logger = logging.getLogger(__name__)


def on_post_migrate(sender, **kwargs):
    """
    Post-migrate signal handler to idempotently set up staff roles and permissions.
    """
    using = kwargs.get("using", DEFAULT_DB_ALIAS)
    try:
        from .services.role_service import setup_roles_and_permissions
        setup_roles_and_permissions(using=using)
    except Exception as e:
        logger.error("Could not setup staff roles during post_migrate on '%s': %s", using, e, exc_info=True)
