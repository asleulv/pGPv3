# myapp/utils.py
from collections import namedtuple
from .models import LegacySong, Song, Round, Vote, Player  # Ensure all relevant models are imported
from django.utils import timezone
from django.db.models import OuterRef, Subquery, Sum, Count

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

    # LegacySong winners
    for legacy_song in LegacySong.objects.filter(pgp_plassering='1'):
        round_name = f"pGP#{legacy_song.pgp_num} - {legacy_song.pgp_tema}" if legacy_song.pgp_num else legacy_song.pgp_tema
        winners.append(RoundWinner(
            round_name=round_name,
            organizer=legacy_song.pgp_arr,
            date_added=legacy_song.date_added,
            artist=legacy_song.artist,
            song_title=legacy_song.song,
            spotify_url=legacy_song.spotify_url,
            winning_player_nickname=legacy_song.pgp_levert_av,
        ))

    # Round winners
    latest_rounds = Round.objects.filter(round_finished=True).annotate(
        num_voters=Count('song__vote', distinct=True)
    ).filter(num_voters__gt=0).order_by('-start_date')

    for round_instance in latest_rounds:
        # Get all songs for the round ordered by score
        songs = (
            Song.objects.filter(round=round_instance)
            .annotate(voter_count=Count('vote__player', distinct=True))
            .order_by('-total_score', '-voter_count')  # Highest score first
        )

        # Find a valid winner
        valid_winner = None
        for song in songs:
            # Check if the player who submitted this song voted for other songs
            has_voted = Vote.objects.filter(
                player=song.player,
                song__round=round_instance
            ).exclude(song=song).exists()

            if has_voted:
                valid_winner = song
                break

        if valid_winner:
            winners.append(RoundWinner(
                round_name=round_instance.name,
                organizer=round_instance.organizer.player.nickname,
                date_added=round_instance.start_date.strftime('%Y-%m-%d'),
                artist=valid_winner.artist,
                song_title=valid_winner.title,
                spotify_url=valid_winner.spotify_url,
                winning_player_nickname=valid_winner.player.nickname,
            ))

    # Sort winners by date_added (latest first)
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
            .order_by('-total_points')
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
            .order_by('-total_points')
        )
    
    def top_score_12_songs(self):
        """
        Get a list of songs where the logged-in player has given a score of 12.
        Includes Spotify URL and round information.
        """
        return (
            Vote.objects.filter(player=self.player, score=12)
            .select_related('song')  # Ensure the song is fetched
            .prefetch_related('song__round')  # Prefetch the related round for efficient querying
            .values('song__title', 'song__artist', 'song__spotify_url', 'song__round__id', 'song__round__name')
            .order_by('-song__id')  # Apply ordering here
        )
    


# Add this to your existing utils.py file
def get_user_chart_data(player):
    """
    Generate chart data for user's ranking progression over time
    Returns None if no data available
    """
    if not player:
        return None
    
    user_rounds = []
    user_ranks = []
    
    # Get all finished rounds that the user participated in
    user_songs = Song.objects.filter(
        player=player, 
        round__round_finished=True
    ).select_related('round').order_by('round__start_date')
    
    for song in user_songs:
        round_obj = song.round
        
        # Get all songs in this round with their scores, ordered by score (descending)
        all_songs_in_round = Song.objects.filter(round=round_obj).order_by('-total_score')
        
        # Calculate rank (1 = best, 2 = second best, etc.)
        rank = 1
        for i, round_song in enumerate(all_songs_in_round, 1):
            if round_song.player == player:
                rank = i
                break
        
        user_rounds.append(round_obj.name[:15])  # Truncate long names
        user_ranks.append(rank)
    
    if user_rounds and user_ranks:
        return {
            'labels': user_rounds,
            'data': user_ranks,
            'max_rank': max(user_ranks) if user_ranks else 10  # For chart scaling
        }
    
    return None

