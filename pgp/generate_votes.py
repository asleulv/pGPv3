# generate_votes.py

import os
import random
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from app.models import Round, Song, Vote, Player

# Specify the round ID
round_id = 35

# Fetch the round
round_instance = Round.objects.get(id=round_id)

# Get all songs and players in the round
songs = list(Song.objects.filter(round=round_instance))
players = list(Player.objects.filter(song__round=round_instance).distinct())

# Generate votes for each player
for player in players:
    # Exclude the player's own songs
    songs_to_vote = [song for song in songs if song.player != player]

    # Shuffle the songs to simulate randomness
    random.shuffle(songs_to_vote)

    # Each player votes for up to 10 songs
    for index, song in enumerate(songs_to_vote[:10]):  # Top 10 songs excluding their own
        Vote.objects.create(
            song=song,
            player=player,
            score=10 - index  # Distribute points (10 for the first, 9 for the second, etc.)
        )

print(f"Votes successfully created for Round ID {round_id}, excluding self-votes!")
