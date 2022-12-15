import os

import spotipy
from phue import Bridge
from spotipy import Spotify
from fastapi import FastAPI
from dotenv import load_dotenv

from src.spotihue import SpotiHue


load_dotenv()


spotify = Spotify(
    auth=spotipy.util.prompt_for_user_token(
        os.environ.get("SPOTIFY_USERNAME"),
        os.environ.get("SPOTIFY_SCOPE"),
        os.environ.get("SPOTIFY_CLIENT_ID"),
        os.environ.get("SPOTIFY_CLIENT_SECRET"),
        os.environ.get("SPOTIFY_REDIRECT_URI")
    )
)
hue = Bridge(os.environ.get("HUE_BRIDGE_IP_ADDRESS"))


spotihue = SpotiHue(spotify, hue)


app = FastAPI()


@app.get("/current-track-information/")
async def retrieve_current_track_information():
    track_name, track_artist,\
        track_album, track_album_artwork_url = spotihue.retrieve_current_track_information()
    return {
        "track_name": track_name,
        "track_artist": track_artist,
        "track_album": track_album,
        "track_album_artwork_url": track_album_artwork_url
    }
    

@app.put("/start-spotihue/")
async def stop_spotihue():
    spotihue.turn_lights_on()
    return True


@app.put("/execute-spotihue/")
async def execute_spotihue():
    track_name, track_artist,\
        track_album, track_album_artwork_url = spotihue.sync_music_lights(
            last_track_name="",
            last_track_artist="",
            track_album_artwork_file_path="album-artwork.jpeg",
            k=3
        )
    return {
        "track_name": track_name,
        "track_artist": track_artist,
        "track_album": track_album,
        "track_album_artwork_url": track_album_artwork_url
    }


@app.put("/stop-spotihue/")
async def stop_spotihue():
    spotihue.change_light_color_normal()
    return False
