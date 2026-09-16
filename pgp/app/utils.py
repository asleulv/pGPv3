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


def get_form_chart_data(limit=10):
    """
    Generate form statistics and chart data over the last `limit` finished rounds.
    Returns a dict with 'num_rounds', 'leaderboard', and 'chart_data'.
    """
    finished_rounds = list(Round.objects.filter(round_finished=True).order_by('-start_date')[:limit])
    
    # Fallback for dev/test environments where rounds have songs but round_finished is not set True yet
    if not finished_rounds:
        finished_rounds = list(Round.objects.filter(song__isnull=False).distinct().order_by('-start_date')[:limit])

    if not finished_rounds:
        return None

    # Chronological order (oldest to newest among last `limit` rounds)
    finished_rounds.reverse()

    round_ids = [r.id for r in finished_rounds]
    round_labels = [r.name[:15] for r in finished_rounds]

    # Map (player_id, round_id) -> score
    songs = Song.objects.filter(round_id__in=round_ids).select_related('player', 'round')
    
    player_scores = {}  # player_id -> {round_id -> score}
    players_dict = {}   # player_id -> Player object

    for song in songs:
        p_id = song.player_id
        r_id = song.round_id
        if p_id not in player_scores:
            player_scores[p_id] = {}
            players_dict[p_id] = song.player
        player_scores[p_id][r_id] = song.total_score

    if not player_scores:
        return None

    # Calculate form stats for each player
    leaderboard = []
    for p_id, rounds_map in player_scores.items():
        player = players_dict[p_id]
        scores_list = [rounds_map.get(r_id, None) for r_id in round_ids]
        valid_scores = [s for s in scores_list if s is not None]
        total_points = sum(valid_scores)
        rounds_played = len(valid_scores)
        avg_points = round(total_points / rounds_played, 1) if rounds_played > 0 else 0

        leaderboard.append({
            'player_id': p_id,
            'nickname': player.nickname,
            'user_id': player.user_id,
            'total_points': total_points,
            'rounds_played': rounds_played,
            'avg_points': avg_points,
            'scores_history': scores_list,
            'recent_scores': valid_scores[-5:],
        })

    # Sort leaderboard by total_points descending, then avg_points
    leaderboard.sort(key=lambda x: (x['total_points'], x['avg_points']), reverse=True)

    # Colors palette for Chart.js datasets
    colors = [
        '#6366f1', # Indigo
        '#10b981', # Emerald
        '#f59e0b', # Amber
        '#ec4899', # Pink
        '#8b5cf6', # Purple
        '#06b6d4', # Cyan
        '#ef4444', # Red
        '#3b82f6', # Blue
    ]

    top_players = leaderboard[:8]
    datasets = []
    for idx, p_stat in enumerate(top_players):
        color = colors[idx % len(colors)]
        datasets.append({
            'label': f"@{p_stat['nickname']}",
            'data': p_stat['scores_history'],
            'borderColor': color,
            'backgroundColor': color + '20',
            'borderWidth': 3,
            'tension': 0.35,
            'pointRadius': 4,
            'pointHoverRadius': 7,
            'spanGaps': True,
        })

    return {
        'num_rounds': len(finished_rounds),
        'leaderboard': leaderboard,
        'chart_data': {
            'labels': round_labels,
            'datasets': datasets,
        }
    }


