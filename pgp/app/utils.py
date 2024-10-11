# myapp/utils.py
from collections import namedtuple
from .models import LegacySong, Song  # Ensure all relevant models are imported
from django.utils import timezone

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
