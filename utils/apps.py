from django.apps import AppConfig


class UtilsConfig(AppConfig):
    name = 'utils'
    verbose_name = 'Utilities'

    def ready(self):
        from utils.ckeditor_webp import patch_ckeditor_upload
        patch_ckeditor_upload()
