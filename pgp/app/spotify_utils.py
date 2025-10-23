
import re
import requests
import logging

logger = logging.getLogger(__name__)


def resolve_spotify_url(spotify_url):
    """
    Resolves Spotify URLs to track ID.
    For spotify.link URLs, extracts from HTML content of spotify.app.link redirect.
    """
    
    if not spotify_url or not isinstance(spotify_url, str):
        return None, None
    
    spotify_url = spotify_url.strip()
    
    # Try to extract track ID directly first
    track_id = extract_track_id(spotify_url)
    if track_id:
        standardized_url = f"https://open.spotify.com/track/{track_id}"
        return standardized_url, track_id
    
    # If it's a spotify.link URL, resolve it
    if 'spotify.link' in spotify_url:
        try:
            # First request to get the Location header (spotify.link -> spotify.app.link)
            response1 = requests.get(
                spotify_url,
                allow_redirects=False,
                timeout=5,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            
            if 'Location' in response1.headers:
                location = response1.headers['Location']
                logger.info(f"Redirected to: {location}")
                
                # Second request to get the HTML from spotify.app.link
                response2 = requests.get(
                    location,
                    allow_redirects=False,
                    timeout=5,
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                
                # Parse HTML for track URL
                if response2.text:
                    track_id = extract_track_id_from_html(response2.text)
                    if track_id:
                        standardized_url = f"https://open.spotify.com/track/{track_id}"
                        logger.info(f"Successfully resolved to: {standardized_url}")
                        return standardized_url, track_id
            
        except requests.RequestException as e:
            logger.error(f"Failed to resolve spotify.link: {str(e)}")
    
    logger.warning(f"Could not extract track ID from URL: {spotify_url}")
    return None, None


def extract_track_id_from_html(html):
    """
    Extracts Spotify track ID from HTML content.
    Looks for open.spotify.com/track/XXXXXX patterns.
    """
    
    match = re.search(r'open\.spotify\.com/track/([a-zA-Z0-9]{22})', html)
    if match:
        track_id = match.group(1)
        logger.info(f"Extracted track ID from HTML: {track_id}")
        return track_id
    
    return None


def extract_track_id(spotify_url):
    """
    Extracts the Spotify track ID from a URL or URI.
    """
    
    if not spotify_url or not isinstance(spotify_url, str):
        return None
    
    spotify_url = spotify_url.strip()
    
    patterns = [
        r'open\.spotify\.com/track/([a-zA-Z0-9]{22})',
        r'spotify:track:([a-zA-Z0-9]{22})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, spotify_url)
        if match:
            track_id = match.group(1)
            logger.info(f"Extracted track ID: {track_id}")
            return track_id
    
    return None


def validate_spotify_url(spotify_url):
    """
    Quick validation check to see if a URL might be a valid Spotify track URL.
    """
    if not spotify_url:
        return False
    
    spotify_url = spotify_url.strip()
    
    spotify_indicators = [
        'open.spotify.com/track',
        'spotify.link',
        'spotify:track:',
    ]
    
    return any(indicator in spotify_url for indicator in spotify_indicators)