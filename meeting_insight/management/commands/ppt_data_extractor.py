import os
from django.core.management.base import BaseCommand, CommandError
from ...helpers import ppt_data_extractor_helper as helper


class Command(BaseCommand):
    help = 'Extracts data (text, tables, and images) from a PowerPoint (.pptx) file.'

    def add_arguments(self, parser):
        parser.add_argument('ppt_filepath', type=str, help='The path to the PowerPoint file (.pptx)')

    def handle(self, *args, **options):
        ppt_file = options['ppt_filepath']

        if not os.path.exists(ppt_file):
            raise CommandError(f'File not found: {ppt_file}')

        self.stdout.write(self.style.SUCCESS(f'Starting extraction from: {ppt_file}'))

        # Extract the data
        extracted_data = helper.extract_data_from_ppt(ppt_file)

        if extracted_data:
            # Print the extracted data to the console
            helper.print_extracted_data(extracted_data)
            self.stdout.write(self.style.SUCCESS('Data extraction successful!'))
        else:
            self.stdout.write(self.style.ERROR('Data extraction failed.'))
