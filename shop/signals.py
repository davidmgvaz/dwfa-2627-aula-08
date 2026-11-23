"""Invalidação da cache do catálogo · catalogue cache invalidation (Ficha 05)."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .cache import bump_catalogue_version
from .models import Category, Product


@receiver([post_save, post_delete], sender=Category)
@receiver([post_save, post_delete], sender=Product)
def invalidate_catalogue(sender, **kwargs):
    # Qualquer escrita no catálogo → versão nova → as respostas em cache deixam de ser lidas.
    # Any write to the catalogue → new version → cached responses are never read again.
    bump_catalogue_version()
