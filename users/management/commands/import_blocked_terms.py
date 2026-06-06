from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from users.content_moderation import clear_blocked_terms_cache
from users.models import BlockedTerm

DEFAULT_FILE = Path(settings.BASE_DIR) / 'users' / 'data' / 'cmu_bad_words.txt'
CMU_SOURCE_URL = 'https://www.cs.cmu.edu/~biglou/resources/bad-words.txt'


class Command(BaseCommand):
    help = (
        'Import blocked terms from the CMU bad-words list (or a local file). '
        'Existing CMU-sourced terms can be replaced with --replace-cmu.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default=str(DEFAULT_FILE),
            help='Path to a newline-delimited word list.',
        )
        parser.add_argument(
            '--url',
            default='',
            help='Download the word list from this URL instead of using --file.',
        )
        parser.add_argument(
            '--replace-cmu',
            action='store_true',
            help='Delete existing CMU-sourced terms before importing.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show how many terms would be imported without writing to the database.',
        )

    def handle(self, *args, **options):
        if options['url']:
            response = requests.get(options['url'], timeout=30)
            response.raise_for_status()
            raw_lines = response.text.splitlines()
            source_label = options['url']
        else:
            file_path = Path(options['file'])
            if not file_path.exists():
                self.stderr.write(self.style.ERROR(f'File not found: {file_path}'))
                return
            raw_lines = file_path.read_text(encoding='utf-8').splitlines()
            source_label = str(file_path)

        terms = []
        seen = set()
        for line in raw_lines:
            term = line.strip().lower()
            if not term or term.startswith('#'):
                continue
            if term in seen:
                continue
            seen.add(term)
            terms.append(term)

        self.stdout.write(f'Loaded {len(terms)} unique terms from {source_label}')

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('Dry run — no database changes made.'))
            return

        if options['replace_cmu']:
            deleted, _ = BlockedTerm.objects.filter(source=BlockedTerm.SOURCE_CMU).delete()
            self.stdout.write(f'Removed {deleted} existing CMU-sourced terms.')

        existing = set(
            BlockedTerm.objects.filter(term__in=terms).values_list('term', flat=True)
        )
        to_create = [
            BlockedTerm(
                term=term,
                match_mode=BlockedTerm.MATCH_CONTAINS,
                source=BlockedTerm.SOURCE_CMU,
                is_active=True,
            )
            for term in terms
            if term not in existing
        ]

        if to_create:
            BlockedTerm.objects.bulk_create(to_create, ignore_conflicts=True)

        clear_blocked_terms_cache()
        created_count = len(to_create)
        skipped_count = len(terms) - created_count
        self.stdout.write(
            self.style.SUCCESS(
                f'Import complete: {created_count} added, {skipped_count} already present.'
            )
        )
