from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum, F, ExpressionWrapper, fields
from django.db.models import OuterRef, Subquery
from django.db import transaction

class Round(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    playlist_released = models.BooleanField(default=False)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE)
    playlist_url = models.URLField(default='', blank=True)
    release_time = models.DateTimeField(null=True, blank=True)
    round_finished = models.BooleanField(default=False) 

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Set playlist_released to True and record release_time if playlist_url is not empty
        if self.playlist_url and not self.playlist_released:
            self.playlist_released = True
            self.release_time = timezone.now()  # Set the release time to the current time
        super().save(*args, **kwargs)

    def calculate_total_scores(self):
        for song in self.song_set.all():
            total_score = song.vote_set.aggregate(total=models.Sum('score'))['total'] or 0
            song.total_score = total_score
            song.save()

    def update_player_stats(self):
        if not self.round_finished:
            return

        # Get all players in this round
        players = Player.objects.filter(song__round=self).distinct()

        # Define PGP points for top 10
        pgp_points = [12, 10, 8, 7, 6, 5, 4, 3, 2, 1]

        # Collect scores for players in this round
        player_scores = {
            player: player.song_set.filter(round=self).aggregate(total=Sum('vote__score'))['total'] or 0
            for player in players
        }

        # Sort players by their scores for this round (descending order)
        sorted_players = sorted(player_scores.items(), key=lambda x: x[1], reverse=True)

        # Update stats for each player
        for index, (player, score) in enumerate(sorted_players):
            stats, _ = PlayerStats.objects.get_or_create(player=player)

            # Update total points (sum of all scores across all rounds)
            stats.total_points = player.song_set.aggregate(
                total_points=Sum('vote__score')
            )['total_points'] or 0

            # Update PGP points for top 10
            if index < 10:
                stats.total_points_pgp += pgp_points[index]

            # Increment rounds played
            stats.rounds_played += 1

            # Update wins and bottoms
            if index == 0:  # First place in this round
                stats.wins += 1
            if index == len(sorted_players) - 1:  # Last place in this round
                stats.bottoms += 1

            stats.save()

class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=100)

    def __str__(self):
        return self.nickname

class Song(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    spotify_url = models.URLField()
    title = models.CharField(max_length=200)
    artist = models.CharField(max_length=200)
    total_score = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.title} by {self.artist}"

class Vote(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    score = models.IntegerField()

    class Meta:
        unique_together = ('player', 'song')

    def __str__(self):
        return f"{self.player.nickname} -> {self.song.title}: {self.score}"
    
@receiver(post_save, sender=Vote)
def update_song_scores_on_vote_save(sender, instance, **kwargs):
    round_instance = instance.song.round
    round_instance.calculate_total_scores()

@receiver(post_delete, sender=Vote)
def update_song_scores_on_vote_delete(sender, instance, **kwargs):
    round_instance = instance.song.round
    round_instance.calculate_total_scores()

@receiver(post_save, sender=Round)
def call_update_player_stats(sender, instance, **kwargs):
    # Check if the round has been marked as finished and the round was just saved
    if instance.round_finished:
        instance.update_player_stats()


# Player statistics

class PlayerStats(models.Model):
    player = models.OneToOneField(Player, on_delete=models.CASCADE, related_name="stats")
    total_points = models.IntegerField(default=0)
    total_points_pgp = models.IntegerField(default=0)
    rounds_played = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    bottoms = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.player.nickname} Stats"

# THe old pGP-totallista

class LegacySong(models.Model):
    artist = models.CharField(max_length=150)
    song = models.CharField(max_length=150)
    album = models.CharField(max_length=150, blank=True)
    release_year = models.CharField(max_length=4, blank=True)
    date_added = models.CharField(max_length=10, blank=True)
    spotify_url = models.URLField(blank=True)
    pgp_num = models.CharField(max_length=10, blank=True, null=True)
    pgp_tema = models.CharField(max_length=150, blank=True, null=True)
    pgp_arr = models.CharField(max_length=150, blank=True, null=True)
    pgp_plassering = models.CharField(max_length=10, blank=True, null=True)
    pgp_levert_av = models.CharField(max_length=150, blank=True, null=True)

    class Meta:
        db_table = 'pgp'  # Ensure it uses the existing table name if it exists

    def __str__(self):
        return f"{self.song} by {self.artist}"
