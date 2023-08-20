import logging
import os
import random
import time
from typing import Any, List

import celery
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis

from spotihue import constants, spotihue


class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Any = None


if os.path.exists(".env"):
    load_dotenv(".env")

redis_client = redis.Redis(host="redis", port=6379, db=0)

spotihue = spotihue.SpotiHue(
    os.environ.get("SPOTIFY_SCOPE"),
    os.environ.get("SPOTIFY_CLIENT_ID"),
    os.environ.get("SPOTIFY_CLIENT_SECRET"),
    os.environ.get("SPOTIFY_REDIRECT_URI"),
    os.environ.get("HUE_BRIDGE_IP_ADDRESS"),
    redis_client
)

celery_app = celery.Celery("celery_app", broker="redis://redis:6379")
fast_app = FastAPI()


@celery_app.task
def run_spotihue(lights: List[str]) -> None:
    logging.info("Running spotihue")

    while spotihue.ascertain_track_playing():
        last_track_info = redis_client.hgetall(constants.REDIS_TRACK_INFORMATION_KEY)
        last_track_album_artwork_url = last_track_info.get(b"track_album_artwork_url")

        if last_track_album_artwork_url:
            last_track_album_artwork_url = last_track_album_artwork_url.decode("utf-8")

        track_info = spotihue.retrieve_current_track_information()
        track_album_artwork_url = track_info["track_album_artwork_url"]

        redis_client.hset(
            constants.REDIS_TRACK_INFORMATION_KEY,
            mapping=track_info
        )

        if last_track_album_artwork_url != track_album_artwork_url:
            logging.info("Syncing lights")
            spotihue.sync_lights_music(track_album_artwork_url, lights)

        sleep_duration = random.uniform(2, 4)
        time.sleep(sleep_duration)


@fast_app.get("/authorized")
def user_authorized():
    spotihue_auth_manager = spotihue.spotify.auth_manager

    spotify_token = spotihue_auth_manager.validate_token(
        spotihue_auth_manager.cache_handler.get_cached_token()
    )
    token_exists = bool(spotify_token is not None)

    return StandardResponse(success=True, message='Authorized' if token_exists else 'Not Authorized',
                            data={'authorized': token_exists})


@fast_app.get("/available-lights")
async def retrieve_available_lights():
    try:
        available_lights = spotihue.retrieve_available_lights()

        if available_lights:
            response = StandardResponse(
                success=True,
                message="Available lights retrieved successfully",
                data={"lights": available_lights},
            )
        else:
            response = StandardResponse(success=False, message="No available lights")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

    return response


@fast_app.post("/selected-lights")
def store_selected_lights(lights: List[str]):
    if not lights:
        raise HTTPException(status_code=400, detail='\"lights\" list is required.')

    try:
        redis_client.set(constants.REDIS_SELECTED_LIGHTS_KEY, ",".join(lights))

        response = StandardResponse(
            success=True, message="Selected lights list stored in Redis"
        )

    except redis.exceptions.RedisError as redis_err:
        raise HTTPException(status_code=500, detail=f"Redis Error: {str(redis_err)}")

    return response


@fast_app.put("/start-spotihue")
async def start_spotihue(lights: List[str] = None):
    if not lights:
        raise HTTPException(status_code=400, detail='\"lights\" list is required.')

    try:
        task = run_spotihue.delay(lights)
        redis_client.set("spotihue", str(task.id))

        response = StandardResponse(success=True, message="spotihue started")

    except redis.exceptions.RedisError as redis_err:
        raise HTTPException(status_code=500, detail=f"Redis Error: {redis_err}")
    except celery.exceptions.CeleryError as celery_err:
        raise HTTPException(status_code=500, detail=f"Celery Error: {celery_err}")
    except Exception:
        raise HTTPException(status_code=500, detail=f"Internal Server Error")

    return response


@fast_app.get("/current-track-information")
async def retrieve_current_track_information():
    try:
        track_info = redis_client.hgetall(constants.REDIS_TRACK_INFORMATION_KEY)

        response = StandardResponse(
            success=True,
            message="Current track information retrieved successfully",
            data=track_info,
        )

    except redis.exceptions.RedisError as redis_err:
        raise HTTPException(status_code=500, detail=f"Redis Error: {str(redis_err)}")

    return response


@fast_app.put("/stop-spotihue")
async def stop_spotihue():
    try:
        spotihue_status = redis_client.get("spotihue")
        if spotihue_status:
            celery_app.control.revoke(spotihue_status, terminate=True)
            redis_client.delete("spotihue")

            response = StandardResponse(success=True, message="spotihue stopped")
        else:
            response = StandardResponse(success=True, message="spotihue is not running")

    except redis.exceptions.RedisError as redis_err:
        raise HTTPException(status_code=500, detail=f"Redis Error: {redis_err}")
    except celery.exceptions.CeleryError as celery_err:
        raise HTTPException(status_code=500, detail=f"Celery Error: {celery_err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

    return response
