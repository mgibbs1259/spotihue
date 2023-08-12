import os
from typing import List, Union

import uvicorn
from celery import Celery
from fastapi import FastAPI
from fastapi.params import Query
from dotenv import load_dotenv
from pydantic import BaseModel

from spotihue.spotihue import SpotiHue


if os.path.exists(".env"):
    load_dotenv(".env")


spotihue = SpotiHue(
    os.environ.get("SPOTIFY_USERNAME"),
    os.environ.get("SPOTIFY_SCOPE"),
    os.environ.get("SPOTIFY_CLIENT_ID"),
    os.environ.get("SPOTIFY_CLIENT_SECRET"),
    os.environ.get("HUE_BRIDGE_IP_ADDRESS"),
)


app = FastAPI()


class StandardResponse(BaseModel):
    success: bool
    message: str
    data: any = None


@app.get("/available-lights/")
async def retrieve_available_lights():
    available_lights = spotihue.retrieve_available_lights()

    if available_lights:
        response = StandardResponse(
            success=True,
            message="Available lights retrieved successfully",
            data=available_lights,
        )
    else:
        response = StandardResponse(success=False, message="No available lights")

    return response


@app.get("/current-track-information/")
async def retrieve_current_track_information():
    # Get this from Redis for display purposes
    pass


@app.put("/start-spotihue/")
async def start_spotihue(lights: Union[List[str], None] = Query(default=None)):
    try:
        spotihue.change_all_lights_to_normal_color(lights)
        return {"status": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


# Redis to keep track of lights and URL
# Update cache with current track info from celery worker
# Celery worker to run long standing run job
# Kick it off


# @app.put("/execute-spotihue/")
# async def execute_spotihue(
#     lights: Union[List[str], None] = Query(default=None),
#     last_track_album_artwork_url: str = Query(default=None),
# ):
#     try:
#         (
#             track_album,
#             track_artist,
#             track_album,
#             track_album_artwork_url,
#         ) = spotihue.sync_lights_music(lights, last_track_album_artwork_url)
#         return {
#             "track_name": track_name,
#             "track_artist": track_artist,
#             "track_album": track_album,
#             "track_album_artwork_url": track_album_artwork_url,
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/stop-spotihue/")
async def stop_spotihue(lights: Union[List[str], None] = Query(default=None)):
    try:
        spotihue.change_all_lights_to_normal_color(lights)
        return {"status": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
