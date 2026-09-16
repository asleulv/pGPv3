from django.test import TestCase
from app.forms import DynamicVoteForm
from unittest.mock import MagicMock

class DynamicVoteFormTest(TestCase):
    def test_dynamic_vote_form_valid_scores(self):
        song1 = MagicMock(id=1, title="Song 1", artist="Artist 1")
        song2 = MagicMock(id=2, title="Song 2", artist="Artist 2")
        songs = [song1, song2]

        data = {
            'track-1': '12',
            'track-2': '10',
        }
        form = DynamicVoteForm(data=data, songs=songs)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['track-1'], '12')
        self.assertEqual(form.cleaned_data['track-2'], '10')

    def test_dynamic_vote_form_duplicate_scores_invalid(self):
        song1 = MagicMock(id=1, title="Song 1", artist="Artist 1")
        song2 = MagicMock(id=2, title="Song 2", artist="Artist 2")
        songs = [song1, song2]

        # Duplicate score 12 used for both songs
        data = {
            'track-1': '12',
            'track-2': '12',
        }
        form = DynamicVoteForm(data=data, songs=songs)
        self.assertFalse(form.is_valid())


from django.contrib.auth.models import User
from django.utils import timezone
from app.models import Round, Player, Song, Vote

class VoteViewTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password')
        self.user2 = User.objects.create_user(username='user2', password='password')
        
        self.player1 = Player.objects.get(user=self.user1)
        self.player2 = Player.objects.get(user=self.user2)

        self.round = Round.objects.create(
            name='Test Round',
            description='Desc',
            start_date=timezone.now() - timezone.timedelta(days=2),
            end_date=timezone.now() + timezone.timedelta(days=2),
            organizer=self.user1
        )

        self.song1 = Song.objects.create(round=self.round, player=self.player1, title='My Song', artist='My Artist', spotify_url='https://open.spotify.com/track/1')
        self.song2 = Song.objects.create(round=self.round, player=self.player2, title='Other Song', artist='Other Artist', spotify_url='https://open.spotify.com/track/2')

    def test_vote_view_excludes_own_song(self):
        self.client.login(username='user1', password='password')
        response = self.client.get(f'/round/{self.round.pk}/vote/')
        self.assertEqual(response.status_code, 200)
        
        songs_in_context = list(response.context['songs'])
        self.assertNotIn(self.song1, songs_in_context)
        self.assertIn(self.song2, songs_in_context)


from app.utils import get_form_chart_data

class FormChartDataTest(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user(username='player_a', password='pw')
        self.u2 = User.objects.create_user(username='player_b', password='pw')
        self.p1 = Player.objects.get(user=self.u1)
        self.p2 = Player.objects.get(user=self.u2)

        self.r1 = Round.objects.create(
            name='Round 1', description='R1', start_date=timezone.now() - timezone.timedelta(days=10),
            end_date=timezone.now() - timezone.timedelta(days=9), organizer=self.u1, round_finished=True
        )
        self.r2 = Round.objects.create(
            name='Round 2', description='R2', start_date=timezone.now() - timezone.timedelta(days=5),
            end_date=timezone.now() - timezone.timedelta(days=4), organizer=self.u1, round_finished=True
        )

        # Player A: total score 50 (R1=20, R2=30)
        Song.objects.create(round=self.r1, player=self.p1, title='S1', artist='A1', spotify_url='http://sp1', total_score=20)
        Song.objects.create(round=self.r2, player=self.p1, title='S2', artist='A1', spotify_url='http://sp2', total_score=30)

        # Player B: total score 40 (R1=40)
        Song.objects.create(round=self.r1, player=self.p2, title='S3', artist='A2', spotify_url='http://sp3', total_score=40)

    def test_get_form_chart_data(self):
        data = get_form_chart_data(limit=10)
        self.assertIsNotNone(data)
        self.assertEqual(data['num_rounds'], 2)
        leaderboard = data['leaderboard']
        self.assertEqual(len(leaderboard), 2)
        # Player A should be #1 (50p) and Player B #2 (40p)
        self.assertEqual(leaderboard[0]['nickname'], 'player_a')
        self.assertEqual(leaderboard[0]['total_points'], 50)
        self.assertEqual(leaderboard[1]['nickname'], 'player_b')
        self.assertEqual(leaderboard[1]['total_points'], 40)
