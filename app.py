from flask import Flask, render_template, redirect, request, session
import requests
import os
import json
from urllib.parse import urlencode
from spotipy.oauth2 import SpotifyOAuth
import logging
import time
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.getenv('MOODIFY_APP_PASSWORD')

csp_directives = {
    'default-src': '\'self\'',
    'script-src': '\'self\' \'unsafe-inline\' https://ajax.googleapis.com',
    'style-src': '\'self\' \'unsafe-inline\'',
    'img-src': '\'self\' data:',
    'font-src': '\'self\'',
    'frame-src': '\'self\'',
}

@app.after_request
def add_csp_header(response):
    csp = '; '.join([f"{directive} {value}" for directive, value in csp_directives.items()])
    response.headers['Content-Security-Policy'] = csp
    return response

@app.route('/')
def index():
    if 'access_token' not in session:
        return redirect('/login')

    return render_template('index.html')

@app.route('/get_playlists')
def get_playlists():
    access_token = session['access_token']
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    playlists_url = 'https://api.spotify.com/v1/me/playlists'
    playlists_response = make_request(playlists_url, headers)
    playlists_data = json.loads(playlists_response.text)

    if 'items' in playlists_data:
        playlist_details = []
        for playlist in playlists_data['items']:
            playlist_id = playlist['id']
            tracks_url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
            tracks_response = make_request(tracks_url, headers)
            tracks_data = json.loads(tracks_response.text)

            track_ids = [item['track']['id'] for item in tracks_data['items']]
            features_url = f'https://api.spotify.com/v1/audio-features/?ids={",".join(track_ids)}'
            features_response = make_request(features_url, headers)
            features_data = json.loads(features_response.text)

            tempos = []
            moods = []
            for feature in features_data['audio_features']:
                tempo = feature['tempo']
                tempos.append(tempo)

                mood = infer_mood(feature)  
                moods.append(mood)

            mean_tempo = sum(tempos) / len(tempos)
            most_common_mood = max(set(moods), key=moods.count)
            playlist_details.append({
                'name': playlist['name'],
                'tempo': mean_tempo,
                'mood': most_common_mood
            })

        return json.dumps(playlist_details)
    else:
        logging.error("No items in playlists_data. Response was: %s", playlists_data)


    

@app.route('/login')
def login():
    logging.info("Entering login route")
    sp_oauth = SpotifyOAuth(client_id=os.getenv('SPOTIFY_CLIENT_ID'),
                            client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
                            redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
                            scope='playlist-read-private')
    try:
        auth_url = sp_oauth.get_authorize_url()
    except Exception as e:
        logging.error(f"ERROR generating auth url: {e}")
        return str(e), 400

    logging.info(f"Redirecting to {auth_url}")
    return redirect(auth_url)

@app.route('/callback')
def callback():
    logging.info("Entering callback route")
    sp_oauth = SpotifyOAuth(client_id=os.getenv('SPOTIFY_CLIENT_ID'),
                            client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
                            redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
                            scope='playlist-read-private')

    code = request.args.get('code')
    if not code:
        logging.error("ERROR: Code not found in callback.")
        return "Code not found in callback", 400

    try:
        token_info = sp_oauth.get_access_token(code)
    except Exception as e:
        logging.error(f"ERROR retrieving access token: {e}")
        return str(e), 400

    session['access_token'] = token_info['access_token']
    session['refresh_token'] = token_info['refresh_token']  
    return redirect('/')


def infer_mood(features):
    if features['valence'] > 0.7:
        return 'Happy'
    elif features['valence'] < 0.3:
        return 'Sad'
    else:
        return 'Neutral'

def make_request(url, headers):
    response = requests.get(url, headers=headers)
    if response.status_code == 429:
        retry_after = int(response.headers['Retry-After'])
        time.sleep(retry_after)
        return make_request(url, headers)
    elif response.status_code == 401:
        if refresh_access_token():
            headers['Authorization'] = f'Bearer {session["access_token"]}'
            return make_request(url, headers)
        else:
            return redirect('/login')
    return response

def refresh_access_token():
    if 'refresh_token' not in session:
        return False

    sp_oauth = SpotifyOAuth(client_id=os.getenv('SPOTIFY_CLIENT_ID'),
                            client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
                            redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
                            scope='playlist-read-private')
    token_info = sp_oauth.refresh_access_token(session['refresh_token'])
    session['access_token'] = token_info['access_token']
    return True

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
