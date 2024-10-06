# forms.py
from django import forms
from .models import Round, Song, Vote
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class RoundForm(forms.ModelForm):
    class Meta:
        model = Round
        fields = ['name', 'description', 'start_date', 'end_date']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set widgets for date and time fields
        self.fields['start_date'].widget = forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M')
        self.fields['end_date'].widget = forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M')

        # Set widgets for description
        self.fields['description'].widget = forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3
        })

        # Set widgets for name
        self.fields['name'].widget = forms.TextInput(attrs={
            'class': 'form-control'
        })


class SongSubmissionForm(forms.ModelForm):
    class Meta:
        model = Song
        fields = ['spotify_url']
        widgets = {
            'spotify_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'Spotify URL'}),
        }

class VoteForm(forms.Form):
    def __init__(self, *args, **kwargs):
        songs = kwargs.pop('songs', None)
        super().__init__(*args, **kwargs)

        if songs:
            for song in songs:
                self.fields[f'song_{song.id}'] = forms.IntegerField(
                    label=song.title,
                    required=False,  # Allow no vote (no score)
                    widget=forms.NumberInput(attrs={'min': 1, 'max': 12})  # Scoring range adjusted
                )

class DynamicVoteForm(forms.Form):
    def __init__(self, *args, **kwargs):
        songs = kwargs.pop('songs', None)
        super().__init__(*args, **kwargs)
        self.score_range = [12, 10, 8, 7, 6, 5, 4, 3, 2, 1]
        
        
        if songs:
            for song in songs:
                self.fields[f'track-{song.id}'] = forms.ChoiceField(
                    choices=[('', 'Select score')] + [(str(i), str(i)) for i in self.score_range],
                    required=False,
                    label=f'{song.artist} - {song.title}'
                )

    def clean(self):
        cleaned_data = super().clean()
        used_scores = []
        for field_name, score in cleaned_data.items():
            if score:
                if score in used_scores:
                    self.add_error(field_name, f"Score {score} has already been used")
                else:
                    used_scores.append(score)
        return cleaned_data
    
class RegistrationForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput())
    password2 = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords do not match.")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])  # Hash the password
        if commit:
            user.save()
        return user