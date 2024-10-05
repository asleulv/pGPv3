from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from datetime import timedelta
from datetime import datetime
from django.db import models
from .models import Round, Song, Player, Vote
from .forms import RoundForm, SongSubmissionForm, DynamicVoteForm
from .spotify_views import get_spotify_client
from urllib.parse import urlparse
from django import forms
from docx.shared import Pt
from django.db.models import Sum, Value
from django.db.models.functions import Coalesce
import re
from docx import Document
import logging
from django.http import HttpResponseForbidden

@login_required
def home(request):
    return render(request, 'app/home.html')

@login_required
def round_list(request):
    rounds = Round.objects.all().order_by('-start_date')
    return render(request, 'app/round_list.html', {'rounds': rounds, 'now': timezone.now()})

@login_required
def create_round(request):
    if request.method == 'POST':
        form = RoundForm(request.POST)
        if form.is_valid():
            start_date_str = request.POST.get('start_date')
            end_date_str = request.POST.get('end_date')
            start_time_str = request.POST.get('start_time', '00:00')
            end_time_str = request.POST.get('end_time', '00:00')

            try:
                start_datetime = datetime.combine(
                    datetime.strptime(start_date_str, '%Y-%m-%d').date(),
                    datetime.strptime(start_time_str, '%H:%M').time()
                )
                end_datetime = datetime.combine(
                    datetime.strptime(end_date_str, '%Y-%m-%d').date(),
                    datetime.strptime(end_time_str, '%H:%M').time()
                )
            except ValueError:
                messages.error(request, 'Invalid date or time format.')
                return render(request, 'app/create_round.html', {'form': form})

            round = form.save(commit=False)
            round.organizer = request.user
            round.start_date = start_datetime
            round.end_date = end_datetime
            round.save()

            return redirect('round_detail', pk=round.pk)
    else:
        form = RoundForm()
    return render(request, 'app/create_round.html', {'form': form})

def get_track_id(player_song):
    if player_song and player_song.spotify_url:
        parsed_url = urlparse(player_song.spotify_url)
        path_parts = parsed_url.path.split('/')
        if len(path_parts) > 2 and path_parts[1] == 'track':
            return path_parts[2]
    return None

def calculate_countdown(now, release_time):
    time_since_release = now - release_time
    if time_since_release < timedelta(hours=2):
        countdown = timedelta(hours=2) - time_since_release
        total_seconds = int(countdown.total_seconds())
        return f"{total_seconds // 3600}:{(total_seconds // 60) % 60:02}:{total_seconds % 60:02}"
    return None


@login_required
def round_detail(request, pk):
    round_instance = get_object_or_404(Round, pk=pk)
    player = Player.objects.get(user=request.user)
    player_song = Song.objects.filter(round=round_instance, player=player).first()
    has_voted = Vote.objects.filter(player=player, song__round=round_instance).exists()
    
    now = timezone.now()
    
    # Initialize song submission form
    form = SongSubmissionForm(instance=player_song)
    track_id = get_track_id(player_song)
    is_organizer = round_instance.organizer == request.user
    organizer_data = get_organizer_data(round_instance) if is_organizer else {}
    
    release_time = round_instance.release_time if round_instance.playlist_released else None
    countdown = calculate_countdown(now, release_time) if release_time else None

    # Calculate total scores for songs in this round
    all_submitted_songs = Song.objects.filter(round=round_instance).annotate(
        aggregated_score=Coalesce(Sum('vote__score'), Value(0))  # Default to 0 if no votes
    ).order_by('-aggregated_score')

    submitted_player_ids = all_submitted_songs.values_list('player_id', flat=True).distinct()

    player_votes = Vote.objects.filter(player=player, song__round=round_instance) \
        .select_related('song') \
        .order_by('-score')  # Sort votes by score
    
    all_players = Player.objects.filter(id__in=submitted_player_ids)

    # Get the list of players who have voted
    players_with_votes = Vote.objects.filter(song__round=round_instance).values_list('player_id', flat=True).distinct()
    players_with_votes_ids = set(players_with_votes)

    # Get players who have not voted
    players_without_votes = all_players.exclude(id__in=players_with_votes_ids)
    
    has_submitted_song = player_song is not None

    if is_organizer and request.method == "POST" and 'finish_round' in request.POST:
        round_instance.round_finished = True
        round_instance.save()
        return redirect('round_detail', pk=round_instance.pk)
    
    print(f"Players with votes: {players_with_votes}")
    print(f"Players without votes: {players_without_votes}")
    
    # Update the context to include all necessary data for both organizers and players
    context = {
        'round': round_instance,
        'round_finished': round_instance.round_finished, 
        'form': form,
        'player_song': player_song,
        'track_id': track_id,
        'is_organizer': is_organizer,
        'now': now,
        'has_voted': has_voted,
        'release_time': release_time,
        'countdown': countdown,
        'all_submitted_songs': all_submitted_songs,
        'num_submitted_songs': all_submitted_songs.count(),
        'players': Player.objects.filter(id__in=submitted_player_ids), 
        'players_with_votes': Player.objects.filter(id__in=players_with_votes_ids),  # Players who have voted
        'players_without_votes': players_without_votes,  # Players who have not voted
        'votes_dict': {
            song.id: {
                vote.player.id: vote.score for vote in song.vote_set.all()
            }
            for song in all_submitted_songs
        },
        'player_votes': player_votes, 
        'organizer_data': organizer_data,  # Include organizer data if the user is the organizer
        'has_submitted_song': has_submitted_song, 
    }

    return render(request, 'app/round_detail.html', context)



def get_organizer_data(round_instance):
    # This function is no longer needed as we calculate everything in round_detail
    pass


@login_required
def update_playlist_url(request, pk):
    round = get_object_or_404(Round, pk=pk)
    if request.method == 'POST':
        playlist_url = request.POST.get('playlist_url')

        # Validate that the URL is a valid Spotify playlist URL
        if playlist_url and not re.match(r'https?://(open\.spotify\.com|spotify\.com)/playlist/.+', playlist_url):
            messages.error(request, 'Forbanna tosk! Dette er ikkje ei Spotify-liste!')
            return redirect('round_detail', pk=pk)

        # If valid, update the playlist URL
        round.playlist_url = playlist_url
        if playlist_url:
            if not round.playlist_released:  # Set release_time only when first released
                round.release_time = timezone.now()  # Set the release time to current time
            round.playlist_released = True
            messages.success(request, 'pGP-liste publisert!')
        else:
            round.playlist_released = False
            round.release_time = None  # Reset release time if the playlist is removed
            messages.success(request, 'Spotify-liste fjernet!')

        round.save()
        return redirect('round_detail', pk=pk)
    
def remove_playlist(request, pk):
    round = get_object_or_404(Round, pk=pk)
    if request.user == round.organizer:
        round.playlist_url = None
        round.playlist_released = False
        round.save()
    return redirect('round_detail', pk=pk)

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .models import Round, Player, Song
from .forms import SongSubmissionForm
from .spotify import get_spotify_client  # Adjust the import based on your project structure
from urllib.parse import urlparse

@login_required
def submit_song(request, pk):
    round_instance = get_object_or_404(Round, pk=pk)
    player = Player.objects.get(user=request.user)
    player_song = Song.objects.filter(round=round_instance, player=player).first()

    # Check if the current date and time is before the round's start_date
    if timezone.now() > round_instance.start_date:
        messages.error(request, 'Ikke registrert - Fristen har passert!')
        return redirect('round_detail', pk=pk)

    if request.method == 'POST':
        form = SongSubmissionForm(request.POST, instance=player_song)
        if form.is_valid():
            spotify_url = form.cleaned_data['spotify_url']
            
            # Validate and clean the Spotify URL
            parsed_url = urlparse(spotify_url)
            if parsed_url.netloc != 'open.spotify.com' or not parsed_url.path.startswith('/track/'):
                messages.error(request, 'Dette er ikkje ei Spotify-låt-lenke, ditt nek!')
                return redirect('round_detail', pk=pk)
            
            # Create the cleaned URL
            cleaned_spotify_url = f"https://open.spotify.com{parsed_url.path}"
            track_id = cleaned_spotify_url.split('/')[-1]
            sp = get_spotify_client()

            if sp:
                try:
                    track_data = sp.track(track_id)
                    artist_name = track_data['artists'][0]['name']
                    song_title = track_data['name']

                    # Check if the song already exists (same artist and title)
                    existing_song = Song.objects.filter(
                        round=round_instance,
                        title=song_title,
                        artist=artist_name
                    ).exclude(player=player).exists()

                    if existing_song:
                        messages.error(request, '🖐 Stopp! Nokon har allereie levert denne! Prøv igjen med anna låt...')
                        return redirect('round_detail', pk=pk)

                    # If the checks pass, update or create the song
                    Song.objects.update_or_create(
                        round=round_instance,
                        player=player,
                        defaults={
                            'spotify_url': cleaned_spotify_url,
                            'title': song_title,
                            'artist': artist_name
                        }
                    )

                    messages.success(request, 'Bidrag registrert!')
                    return redirect('round_detail', pk=pk)

                except Exception as e:
                    messages.error(request, 'Hmm? Vis dette til Jostein: {}'.format(str(e)))
            else:
                messages.error(request, 'Får ikkje kontakt med Spotify.')
        else:
            messages.error(request, 'Dette er ikkje ei Spotify-låt-lenke, ditt nek!')

    form = SongSubmissionForm(instance=player_song)

    return render(request, 'app/round_detail.html', {
        'round': round_instance,
        'form': form,
        'player_song': player_song,
    })


# View to delete the player's song
def delete_song(request, pk):
    round_obj = get_object_or_404(Round, pk=pk)
    player_song = Song.objects.filter(round=round_obj, player=request.user.player).first()

    if player_song:
        player_song.delete()
        messages.success(request, 'Bidraget ditt ble slettet.')
    else:
        messages.error(request, 'Du har ikke noe bidrag å slette.')

    return redirect('round_detail', pk=pk)


logger = logging.getLogger(__name__)

@login_required
def vote_view(request, pk):
    round_instance = get_object_or_404(Round, pk=pk)
    player = Player.objects.get(user=request.user)
    player_song = Song.objects.filter(round=round_instance, player=player).first()
    songs = Song.objects.filter(round=round_instance).exclude(player=player)

    if request.method == 'POST':
        form = DynamicVoteForm(request.POST, songs=songs)
        logger.debug("Form data: %s", request.POST)
        
        if form.is_valid():
            cleaned_data = form.cleaned_data
            logger.debug("Cleaned data: %s", cleaned_data)
            
            for field_name, score in cleaned_data.items():
                if score:
                    song_id = field_name.split('-')[1]
                    song = get_object_or_404(Song, pk=song_id)
                    
                    # Check if the player has already voted for this song
                    if not Vote.objects.filter(player=player, song=song).exists():
                        Vote.objects.create(player=player, song=song, score=int(score))
                        logger.debug(f"Vote saved: Player {player.nickname}, Song {song.title}, Score {score}")
                    else:
                        logger.warning(f"Duplicate vote attempt: Player {player.nickname}, Song {song.title}, Score {score}")
            
            messages.success(request, '🤩 Poenga dine er registrert!!')
            return redirect('round_detail', pk=pk)
        else:
            logger.error("Form is invalid")
            logger.debug("Form errors: %s", form.errors)
    else:
        form = DynamicVoteForm(songs=songs)

    return render(request, 'app/vote_form.html', {
        'round': round_instance,
        'form': form,
        'songs': songs,
        'player_song': player_song,
        'score_range': form.score_range,
    })

def export_to_word(request, round_id):
    # Get the relevant round
    round_instance = Round.objects.get(id=round_id)
    
    # Get all submitted songs for this round, ordered by total_score (ascending)
    all_submitted_songs = Song.objects.filter(round=round_instance).order_by('total_score')
    
    # Get all players who submitted songs in the current round
    submitted_players = all_submitted_songs.values_list('player', flat=True).distinct()  # Get unique players who submitted songs
    
    # Get players who voted
    voted_players = Vote.objects.filter(song__round=round_instance).values_list('player', flat=True).distinct()
    voted_players_set = set(voted_players)  # Unique players who have voted

    # Identify disqualified players (those who haven't voted)
    disqualified_players = [player for player in submitted_players if player not in voted_players_set]

    # Create a new Document
    doc = Document()

    doc.add_heading(f"Oppsummering av runden: {round_instance.name}", level=1)

    # Add Disqualified players section
    if disqualified_players:
        doc.add_heading("🤢 Diska:", level=2)
        for player_id in disqualified_players:
            player_nickname = Player.objects.get(id=player_id).nickname  # Get the player's nickname
            
            # Get the song details for the player (assuming one song per player for simplicity)
            song = all_submitted_songs.filter(player_id=player_id).first()  # Get the first song submitted by the player
            if song:
                total_score = song.total_score
                artist = song.artist  # Adjust if you need to access the artist differently
                # Add the player nickname with song details in parentheses
                doc.add_paragraph(f"{player_nickname} ({artist} - {song.title}, {total_score} poeng)")

    # Add a blank line before the summary
    doc.add_paragraph("") 

    # Now only include players who have voted in the summary
    for song in all_submitted_songs:
        total_score = song.total_score
        player_nickname = song.player.nickname  # The player who submitted the song
        
        # Check if the player who submitted this song has voted
        if song.player.id in voted_players_set:
            # Write song details to the document
            header_paragraph = doc.add_paragraph()
            run = header_paragraph.add_run(f"{song.artist} - {song.title} ({total_score} poeng)")
            run.bold = True
            run.font.size = Pt(14)  # Set font size for title
            run.font.name = 'Arial'  # Change font family
            
            # Create a new paragraph for "Levert av"
            delivered_paragraph = doc.add_paragraph()
            delivered_run = delivered_paragraph.add_run(f"Levert av: {player_nickname}")
            delivered_run.bold = True
            delivered_run.font.size = Pt(12)  # Set font size for "Levert av"
            delivered_run.font.name = 'Arial'  # Change font family for consistency
            
            doc.add_paragraph("Poeng:")
            
            # Get the votes for the song
            votes = Vote.objects.filter(song=song).order_by('-score')  # Get all votes for the current song, sorted by score descending
            for vote in votes:
                doc.add_paragraph(f"{vote.score} poeng fra {vote.player.nickname}")

            # Add a blank line between songs
            doc.add_paragraph("")  # This adds a line break

    # Prepare the response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    response['Content-Disposition'] = f'attachment; filename="{round_instance.name}_export.docx"'
    
    doc.save(response)  # Save the document to the response
    return response



from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from datetime import datetime
from .models import Round
from .forms import RoundForm

@login_required
def update_round_times(request, round_id):
    round_instance = get_object_or_404(Round, pk=round_id)

    # Check if the user is the organizer
    if request.user != round_instance.organizer:
        messages.error(request, 'You are not authorized to update this round.')
        return redirect('round_detail', round_id=round_instance.id)

    if request.method == "POST":
        form = RoundForm(request.POST, instance=round_instance)
        if form.is_valid():
            start_date_str = request.POST.get('start_date')
            end_date_str = request.POST.get('end_date')
            start_time_str = request.POST.get('start_time', '00:00')
            end_time_str = request.POST.get('end_time', '00:00')

            try:
                start_datetime = datetime.combine(
                    datetime.strptime(start_date_str, '%Y-%m-%d').date(),
                    datetime.strptime(start_time_str, '%H:%M').time()
                )
                end_datetime = datetime.combine(
                    datetime.strptime(end_date_str, '%Y-%m-%d').date(),
                    datetime.strptime(end_time_str, '%H:%M').time()
                )

                # Check if end time is after start time
                if end_datetime <= start_datetime:
                    messages.error(request, 'End time must be after start time.')
                    return render(request, 'rounds/update_round_times.html', {'round': round_instance, 'form': form})

                # Update round times
                round_instance.start_date = start_datetime
                round_instance.end_date = end_datetime
                round_instance.save()

                messages.success(request, 'Round times updated successfully!')
                return redirect('round_detail', round_id=round_instance.id)

            except ValueError:
                messages.error(request, 'Invalid date or time format.')
                return render(request, 'rounds/update_round_times.html', {'round': round_instance, 'form': form})
    else:
        form = RoundForm(instance=round_instance)

    return render(request, 'rounds/update_round_times.html', {'round': round_instance, 'form': form})

