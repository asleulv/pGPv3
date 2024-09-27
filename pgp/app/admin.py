from django.contrib import admin
from . import models

@admin.register(models.Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'playlist_released', 'organizer')
    search_fields = ('name', 'description', 'organizer__username')
    list_filter = ('playlist_released', 'start_date', 'end_date')

@admin.register(models.Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('user', 'nickname')
    search_fields = ('user__username', 'nickname')

@admin.register(models.Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'round', 'player')
    search_fields = ('title', 'artist', 'round__name', 'player__nickname')
    list_filter = ('round', 'player')

@admin.register(models.Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('player', 'song', 'score')
    search_fields = ('player__nickname', 'song__title')
    list_filter = ('score', 'song__round')