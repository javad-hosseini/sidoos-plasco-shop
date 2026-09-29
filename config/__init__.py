"""
Django configuration package initialization.
Includes compatibility shims for Python 3.14+ where standard library changes
affect Django 4.2 template context copying.
"""
import sys

# Python 3.14 compatibility patch for django.template.context.BaseContext.__copy__
# In Python 3.14, copy.copy(super()) returns a super proxy object without __dict__,
# which causes BaseContext.__copy__ to fail when setting duplicate.dicts.
if sys.version_info >= (3, 14):
    try:
        import django.template.context

        def _base_context_copy(self):
            duplicate = object.__new__(self.__class__)
            duplicate.__dict__.update(self.__dict__)
            duplicate.dicts = self.dicts[:]
            return duplicate

        django.template.context.BaseContext.__copy__ = _base_context_copy
    except ImportError:
        pass
