# management/commands/import_legacy_songs.py

import sqlite3
from django.core.management.base import BaseCommand
from app.models import LegacySong  # Update to your app name
import os

class Command(BaseCommand):
    help = 'Import songs from the legacy SQLite database'

    def handle(self, *args, **options):
        # Get the absolute path to the database
        db_path = os.path.join(os.path.dirname(__file__), 'app_.db')
        conn = sqlite3.connect(db_path)  # Connect using the absolute path
        cursor = conn.cursor()

        # Fetch all records from the pgp table
        cursor.execute("SELECT * FROM pgp")
        records = cursor.fetchall()

        # Iterate through the records and create LegacySong objects
        for record in records:
            LegacySong.objects.create(
                artist=record[1],
                song=record[2],
                album=record[3],
                release_year=record[4],
                date_added=record[5],
                spotify_url=record[6],
                pgp_num=record[7],
                pgp_tema=record[8],
                pgp_arr=record[9],
                pgp_plassering=record[10],
                pgp_levert_av=record[11],
            )

        # Close the SQLite connection
        conn.close()

        self.stdout.write(self.style.SUCCESS('Successfully imported songs into LegacySong model.'))
