from django.contrib import admin
from django.utils import timezone
from . import models

# For superusers, this remains the same
@admin.register(models.Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'playlist_released', 'organizer')
    search_fields = ('name', 'description', 'organizer__username')
    list_filter = ('playlist_released', 'start_date', 'end_date')

    # Limit the queryset for non-admin users (organizers)
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # Admin users can see all rounds
        return qs.filter(organizer=request.user)  # Non-admin users can only see their own rounds

    # Automatically set the organizer to the logged-in user when creating a round
    def save_model(self, request, obj, form, change):
        if not change:  # Only set the organizer when creating a new round
            obj.organizer = request.user
        obj.save()

    # Restrict editing if the end date has passed for non-superusers
    def get_readonly_fields(self, request, obj=None):
        # Allow editing for staff users, but restrict for regular users
        if obj and obj.end_date < timezone.now() and not request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]  # All fields are read-only
        return self.readonly_fields

    # Prevent non-admin users from deleting rounds after the end date has passed
    def has_delete_permission(self, request, obj=None):
        if obj and obj.end_date < timezone.now() and not request.user.is_superuser:
            return False
        return True

# Register the Player model (visible only to superusers)
@admin.register(models.Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('user', 'nickname')
    search_fields = ('user__username', 'nickname')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # Only allow superusers to see this
        return qs.none()  # Non-admins cannot see Player data

# Register the Song model (visible only to superusers)
@admin.register(models.Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'round', 'get_obfuscated_player')
    search_fields = ('title', 'artist', 'round__name', 'player__nickname')
    list_filter = ('round',)

    def get_obfuscated_player(self, obj):
        # Slur the player's nickname to hide their identity
        return '🔒'  # Replace this with any kind of obfuscation you prefer

    get_obfuscated_player.short_description = 'Player'  # Name to display in admin

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # Superusers can see everything
        return qs  # Non-admins will see the obfuscated player names
    
@admin.register(models.LegacySong)
class LegacySongAdmin(admin.ModelAdmin):
    list_display = ('song', 'artist', 'pgp_tema', 'pgp_levert_av')  # Equivalent to 'title', 'artist', 'round', 'player'
    search_fields = ('song', 'artist', 'pgp_tema', 'pgp_levert_av')  # Search by song, artist, round (pgp_tema), and player (pgp_levert_av)
    list_filter = ('pgp_tema', 'pgp_levert_av')  # Filter by round (pgp_tema) and player (pgp_levert_av)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # Only allow superusers to see this
        return qs.none()  # Non-admins cannot see LegacySong data

# Register the Vote model (visible only to superusers)
@admin.register(models.Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('player', 'song', 'score')
    search_fields = ('player__nickname', 'song__title')
    list_filter = ('score', 'song__round')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # Only allow superusers to see this
        return qs.none()  # Non-admins cannot see Vote data
