from django.core.management.base import BaseCommand

from apps.blogs.models import Article


class Command(BaseCommand):
    help = 'Delete all mock articles from the database'

    def handle(self, *args, **options):
        self.stdout.write('🗑️  Deleting all articles...')

        count = Article.objects.count()
        Article.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(f'✅ Deleted {count} articles'))
