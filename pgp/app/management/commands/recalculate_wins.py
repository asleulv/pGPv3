# Create file: app/management/commands/recalculate_wins.py

from django.core.management.base import BaseCommand
from django.db.models import Sum
from app.models import Round, Player, PlayerStats

class Command(BaseCommand):
    help = 'Recalculate wins and bottoms for all finished rounds'

    def handle(self, *args, **options):
        finished_rounds = Round.objects.filter(round_finished=True).order_by('end_date')
        
        for round_obj in finished_rounds:
            self.stdout.write(f"Processing round: {round_obj.name}")
            round_obj.update_player_stats()
        
        self.stdout.write(self.style.SUCCESS('✅ Wins recalculated for all finished rounds!'))
