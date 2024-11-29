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

        players = Player.objects.filter(song__round=self).distinct()

        # Gather the scores for all players in the round
        player_scores = []
        for player in players:
            total_points = player.song_set.filter(round=self).aggregate(
                total_score=Sum('vote__score')
            )['total_score'] or 0

            player_scores.append((player, total_points))

        # Sort players by total points in descending order
        player_scores.sort(key=lambda x: x[1], reverse=True)

        # Assign PGP points to the top 10 players
        pgp_points = [12, 10, 8, 7, 6, 5, 4, 3, 2, 1]  # Points distribution for top 10
        for index, (player, points) in enumerate(player_scores[:10]):
            stats, created = PlayerStats.objects.get_or_create(player=player)
            stats.total_points_pgp += pgp_points[index]  # Add PGP-style points
            stats.save()

        # Update other player stats
        for player in players:
            total_points = player.song_set.filter(round=self).aggregate(
                total_score=Sum('vote__score')
            )['total_score'] or 0

            highest_score_song = player.song_set.filter(round=self).annotate(
                max_score=ExpressionWrapper(
                    F('vote__score'), output_field=fields.IntegerField()
                )
            ).order_by('-max_score').first()

            lowest_score_song = player.song_set.filter(round=self).annotate(
                min_score=ExpressionWrapper(
                    F('vote__score'), output_field=fields.IntegerField()
                )
            ).order_by('min_score').first()

            total_votes = player.song_set.filter(round=self).aggregate(
                total_votes=Sum('vote__score')
            )['total_votes'] or 0
            num_songs = player.song_set.filter(round=self).count()
            average_score = total_votes / num_songs if num_songs > 0 else 0

            stats, created = PlayerStats.objects.get_or_create(player=player)
            stats.total_points = total_points
            stats.highest_score_song = highest_score_song.title if highest_score_song else ''
            stats.highest_score = highest_score_song.vote_set.aggregate(
                highest=models.Max('score')
            )['highest'] if highest_score_song else 0
            stats.lowest_score_song = lowest_score_song.title if lowest_score_song else ''
            stats.lowest_score = lowest_score_song.vote_set.aggregate(
                lowest=models.Min('score')
            )['lowest'] if lowest_score_song else 0
            stats.average_score = average_score
            stats.rounds_played += 1

            # Update wins and bottoms
            if player_scores.index((player, total_points)) == 0:
                stats.wins += 1  # Increment wins if the player is the 1st place
            if player_scores.index((player, total_points)) == len(player_scores) - 1:
                stats.bottoms += 1  # Increment bottoms if the player is in the last place

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
    highest_score_song = models.CharField(max_length=200, blank=True, null=True)
    highest_score = models.IntegerField(default=0)
    lowest_score_song = models.CharField(max_length=200, blank=True, null=True)
    lowest_score = models.IntegerField(default=0)
    organizer_history = models.JSONField(default=list, blank=True)
    average_score = models.FloatField(default=0)
    rounds_played = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    bottoms = models.IntegerField(default=0)
    disqualifications = models.IntegerField(default=0)

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
