"""
Django configuration package initialization.
Includes compatibility shims for Python 3.14+ where standard library changes
affect Django 4.2 template context copying.
"""
import sys

# Python 3.14 / Django 6.0 compatibility patches
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

    try:
        import django.db.models
        if hasattr(django.db.models, 'CheckConstraint'):
            _orig_cc_init = django.db.models.CheckConstraint.__init__
            def _compat_cc_init(self, *args, **kwargs):
                if 'check' in kwargs and 'condition' not in kwargs:
                    kwargs['condition'] = kwargs.pop('check')
                _orig_cc_init(self, *args, **kwargs)
            django.db.models.CheckConstraint.__init__ = _compat_cc_init
    except ImportError:
        pass
