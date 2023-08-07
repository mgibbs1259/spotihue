import os
from typing import List, Union

import spotipy
import uvicorn
from phue import Bridge
from spotipy import Spotify
from fastapi import FastAPI
from fastapi.params import Query
from dotenv import load_dotenv

from spotihue.spotihue import SpotiHue


load_dotenv()


spotify = Spotify(
    auth=spotipy.util.prompt_for_user_token(
        os.environ.get("SPOTIFY_USERNAME"),
        os.environ.get("SPOTIFY_SCOPE"),
        os.environ.get("SPOTIFY_CLIENT_ID"),
        os.environ.get("SPOTIFY_CLIENT_SECRET"),
        os.environ.get("SPOTIFY_REDIRECT_URI"),
    )
)


hue = Bridge(os.environ.get("HUE_BRIDGE_IP_ADDRESS"))
hue.connect()


spotihue = SpotiHue(spotify, hue)


app = FastAPI()


@app.get("/available-lights/")
async def retrieve_light_information():
    try:
        return [light.name for light in hue.lights]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/current-track-information/")
async def retrieve_current_track_information():
    try:
        (
            track_name,
            track_artist,
            track_album,
            track_album_artwork_url,
        ) = spotihue.retrieve_current_track_information()
        return {
            "track_name": track_name,
            "track_artist": track_artist,
            "track_album": track_album,
            "track_album_artwork_url": track_album_artwork_url,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/start-spotihue/")
async def start_spotihue(lights: Union[List[str], None] = Query(default=None)):
    try:
        spotihue.change_all_lights_to_normal_color(lights)
        return {"status": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/execute-spotihue/")
async def execute_spotihue(
    lights: Union[List[str], None] = Query(default=None),
    last_track_album_artwork_url: str = Query(default=None),
):
    try:
        (
            track_album,
            track_artist,
            track_album,
            track_album_artwork_url,
        ) = spotihue.sync_lights_music(lights, last_track_album_artwork_url)
        return {
            "track_name": track_name,
            "track_artist": track_artist,
            "track_album": track_album,
            "track_album_artwork_url": track_album_artwork_url,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/stop-spotihue/")
async def stop_spotihue(lights: Union[List[str], None] = Query(default=None)):
    try:
        spotihue.change_all_lights_to_normal_color(lights)
        return {"status": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
