"""
Domain layer package.

Contains pure business logic (entities, value objects, exceptions).
This package must be independent of infrastructure and delivery mechanisms.

TODO:
- Populate domain.entities and domain.value_objects with concrete classes.
"""
from . import exceptions

__all__ = ["exceptions"]