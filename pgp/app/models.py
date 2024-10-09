from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum

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
