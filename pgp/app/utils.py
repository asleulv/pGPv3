# myapp/utils.py
from collections import namedtuple
from .models import LegacySong, Song, Round, Vote, Player  # Ensure all relevant models are imported
from django.utils import timezone
from django.db.models import OuterRef, Subquery, Sum

def get_combined_song_data():
    CombinedSong = namedtuple('CombinedSong', [
        'dato',      # The release_time in Round or date_added in LegacySong
        'artist',    # The artist in Song or LegacySong
        'tittel',    # The title in Song or song in LegacySong
        'levert_av', # The Player in Song or pgp_levert_av in LegacySong
        'tema',      # The Round in Song or pgp_tema in LegacySong
        'spotify'    # The spotify_url in Song or LegacySong
    ])
    
    combined_songs = []

    # Fetch all Song instances and add them to combined_songs
    for song in Song.objects.all():
        if song.round and song.round.round_finished:  # Ensure the round exists and is finished
            release_time = song.round.release_time
            if release_time:  # Ensure it's not None
                if isinstance(release_time, timezone.datetime):  # Check if release_time is a datetime object
                    release_time = release_time.strftime('%Y-%m-%d')  # Format to DD-MM-YYYY
                # Add the song only if the round is finished
                combined_songs.append(CombinedSong(
                    dato=release_time,
                    artist=song.artist,
                    tittel=song.title,
                    levert_av=song.player.nickname,
                    tema=song.round.name,  # This is safe since we know round is not None
                    spotify=song.spotify_url
                ))

    # Fetch all LegacySong instances and add them to combined_songs
    for legacy_song in LegacySong.objects.all():
        date_added = legacy_song.date_added
        if date_added:  # Ensure it's not None
             # Format to DD-MM-YYYY
            combined_songs.append(CombinedSong(
                dato=date_added,
                artist=legacy_song.artist,
                tittel=legacy_song.song,
                levert_av=legacy_song.pgp_levert_av,
                tema=legacy_song.pgp_tema,
                spotify=legacy_song.spotify_url
            ))

    return combined_songs

def get_round_winners():
    RoundWinner = namedtuple('RoundWinner', [
        'round_name',           
        'organizer',            
        'date_added',           
        'artist',               
        'song_title',           
        'spotify_url',          
        'winning_player_nickname'  
    ])

    winners = []

    # Fetch all LegacySong instances where pgp_plassering is '1' (first place)
    for legacy_song in LegacySong.objects.filter(pgp_plassering='1'):
        round_name = f"pGP#{legacy_song.pgp_num} - {legacy_song.pgp_tema}" if legacy_song.pgp_num else legacy_song.pgp_tema
        winners.append(RoundWinner(
            round_name=round_name,
            organizer=legacy_song.pgp_arr,
            date_added=legacy_song.date_added,  # Keep as text
            artist=legacy_song.artist,
            song_title=legacy_song.song,
            spotify_url=legacy_song.spotify_url,
            winning_player_nickname=legacy_song.pgp_levert_av,
        ))

    latest_round_winners = (
        Round.objects.filter(round_finished=True)
        .annotate(
            winning_score=Subquery(
                Song.objects.filter(round=OuterRef('id'))
                .order_by('-total_score')
                .values('total_score')[:1]
            )
        )
        .filter(winning_score__gt=0)
        .annotate(
            winning_song_title=Subquery(
                Song.objects.filter(round=OuterRef('id'))
                .order_by('-total_score')
                .values('title')[:1]
            ),
            winning_artist=Subquery(
                Song.objects.filter(round=OuterRef('id'))
                .order_by('-total_score')
                .values('artist')[:1]
            ),
            winning_spotify_url=Subquery(
                Song.objects.filter(round=OuterRef('id'))
                .order_by('-total_score')
                .values('spotify_url')[:1]
            ),
            winning_player_nickname=Subquery(
                Song.objects.filter(round=OuterRef('id'))
                .order_by('-total_score')
                .values('player__nickname')[:1]
            )
        )
        .values(
            'name', 
            'organizer__player__nickname', 
            'start_date',
            'winning_song_title',
            'winning_artist',
            'winning_spotify_url',
            'winning_player_nickname'
        )
        .order_by('-start_date')  # This ensures the latest rounds are first
    )

    for winner in latest_round_winners:
        winners.append(RoundWinner(
            round_name=winner['name'],
            organizer=winner['organizer__player__nickname'],
            date_added=winner['start_date'].strftime('%Y-%m-%d'),  # Keep as text
            artist=winner['winning_artist'],
            song_title=winner['winning_song_title'],
            spotify_url=winner['winning_spotify_url'],
            winning_player_nickname=winner['winning_player_nickname']
        ))

    # Sort the winners list by date_added as text (since it's in the format 'YYYY-MM-DD')
    winners.sort(key=lambda x: x.date_added, reverse=True)

    return winners


class LoggedInPlayerStats:
    def __init__(self, user):
        self.player = Player.objects.get(user=user)

    def previous_songs(self):
        """
        Get a list of songs submitted by the logged-in player.
        Includes Spotify URL and round information.
        """
        return Song.objects.filter(player=self.player).select_related('round').values(
            'title', 'artist', 'spotify_url', 'round__id', 'round__name'
        )

    def top_voters(self):
        """
        Get a list of the top players who voted for the logged-in player's songs,
        sorted by the total points given.
        """
        return (
            Vote.objects.filter(song__player=self.player)
            .values('player__nickname')
            .annotate(total_points=Sum('score'))
            .order_by('-total_points')[:10]
        )

    def top_given_votes(self):
        """
        Get a list of players the logged-in player gave the most points to,
        sorted by total points given.
        """
        return (
            Vote.objects.filter(player=self.player)
            .values('song__player__nickname')
            .annotate(total_points=Sum('score'))
            .order_by('-total_points')[:10]
        )


