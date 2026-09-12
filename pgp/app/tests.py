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
