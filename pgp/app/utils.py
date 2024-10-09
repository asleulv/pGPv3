# myapp/utils.py
from collections import namedtuple
from .models import LegacySong, Song  # Ensure all relevant models are imported

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
        combined_songs.append(CombinedSong(
            dato=song.round.release_time if song.round else None,
            artist=song.artist,
            tittel=song.title,
            levert_av=song.player.nickname,
            tema=song.round.name if song.round else None,
            spotify=song.spotify_url
        ))

    # Fetch all LegacySong instances and add them to combined_songs
    for legacy_song in LegacySong.objects.all():
        combined_songs.append(CombinedSong(
            dato=legacy_song.date_added,
            artist=legacy_song.artist,
            tittel=legacy_song.song,
            levert_av=legacy_song.pgp_levert_av,
            tema=legacy_song.pgp_tema,
            spotify=legacy_song.spotify_url
        ))

    return combined_songs
