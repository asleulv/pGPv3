from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),
    path('my_rounds/', views.my_rounds, name='my_rounds'),
    path('edit_round/<int:round_id>/', views.edit_round, name='edit_round'),
    path('create-round/', views.create_round, name='create_round'),
    path('round/<int:pk>/', views.round_detail, name='round_detail'),
    path('round/<int:pk>/submit-song/', views.submit_song, name='submit_song'),
    path('round/<int:pk>/delete/', views.delete_song, name='delete_song'),
    path('round/<int:pk>/update-playlist/', views.update_playlist_url, name='update_playlist_url'),
    path('round/<int:pk>/remove_playlist/', views.remove_playlist, name='remove_playlist'),
    path('round/<int:pk>/vote/', views.vote_view, name='vote_form'),  
    path('rounds/', views.round_list, name='round_list'),
    path('export/word/<int:round_id>/', views.export_to_word, name='export_to_word'),
    path('combined-songs/data/', views.combined_song_data_view, name='combined_song_data_view'),
    path('combined-songs/', views.combined_song_view, name='combined-songs'),

]
