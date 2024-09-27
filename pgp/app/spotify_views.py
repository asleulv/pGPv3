from django.conf import settings
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

def get_spotify_client():
    client_id = settings.SPOTIPY_CLIENT_ID
    client_secret = settings.SPOTIPY_CLIENT_SECRET
    credentials = SpotifyClientCredentials(client_id, client_secret)
    return Spotify(auth_manager=credentials)