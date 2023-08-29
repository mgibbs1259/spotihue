import os
import time
import random
import logging
from typing import Any, List

import redis
import celery
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from spotihue import constants, spotihue


logger = logging.getLogger(__name__)


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
    redis_client,
)

celery_app = celery.Celery("celery_app", broker="redis://redis:6379")

fast_app = FastAPI()


@celery_app.task
def run_spotihue(lights: List[str]) -> None:
    logger.info("Running spotihue")

    # This is a placeholder for PR #8
    spoithue._hue.change_all_lights_to_white(lights)

    while spotihue.ascertain_track_playing():
        last_track_info = redis_client.hgetall(constants.REDIS_TRACK_INFORMATION_KEY)
        last_track_album_artwork_url = last_track_info.get(b"track_album_artwork_url")

        if last_track_album_artwork_url:
            last_track_album_artwork_url = last_track_album_artwork_url.decode("utf-8")

        track_info = spotihue.retrieve_current_track_information()
        track_album_artwork_url = track_info["track_album_artwork_url"]

        redis_client.hset(constants.REDIS_TRACK_INFORMATION_KEY, mapping=track_info)

        if last_track_album_artwork_url != track_album_artwork_url:
            logger.info("Syncing lights")
            spotihue.sync_lights_music(track_album_artwork_url, lights)

        sleep_duration = random.uniform(2, 4)
        time.sleep(sleep_duration)


@fast_app.get("/spotify-ready")
def spotify_authorized():
    spotify_auth_manager = spotihue.spotify_oauth

    spotify_token = spotify_auth_manager.validate_token(
        spotify_auth_manager.cache_handler.get_cached_token()
    )
    token_exists = bool(spotify_token is not None)

    return StandardResponse(
        success=True,
        message="Authorized" if token_exists else "Not Authorized",
        data={"ready": token_exists},
    )


@fast_app.get("/available-lights")
async def retrieve_available_lights():
    try:
        available_lights = spotihue.retrieve_available_lights()

        if available_lights:
            response = StandardResponse(
                success=True,
                message="Available lights retrieved successfully",
                data=available_lights,
            )
        else:
            response = StandardResponse(
                success=True, message="No available lights", data=available_lights
            )

    except Exception as e:
        logger.error(f"Error retrieving available lights: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return response


@fast_app.post("/selected-lights")
def store_selected_lights(lights: List[str]):
    if not lights:
        raise HTTPException(status_code=400, detail='"lights" list is required.')

    try:
        redis_client.set(constants.REDIS_SELECTED_LIGHTS_KEY, ",".join(lights))

        return StandardResponse(
            success=True, message="Selected lights list stored in Redis"
        )

    except redis.exceptions.RedisError as redis_err:
        logger.error(f"Redis error storing selected lights: {redis_err}")
        raise HTTPException(status_code=500, detail=f"Redis Error")


@fast_app.put("/start-spotihue")
async def start_spotihue(lights: List[str] = None):
    if not lights:
        raise HTTPException(status_code=400, detail='"lights" list is required.')

    available_lights = spotihue.retrieve_available_lights()
    lights = [light for light in lights if light in available_lights]

    try:
        # TODO: make this idempotent

        task = run_spotihue.delay(lights)
        redis_client.set("spotihue", str(task.id))

        return StandardResponse(success=True, message="spotihue started")

    except redis.exceptions.RedisError as redis_err:
        logger.error(f"Redis error starting spotihue: {redis_err}")
        raise HTTPException(status_code=500, detail=f"Redis Error")
    except celery.exceptions.CeleryError as celery_err:
        logger.error(f"Celery error starting spotihue: {celery_err}")
        raise HTTPException(status_code=500, detail=f"Celery Error")
    except Exception as e:
        logger.error(f"Error starting spotihue: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error")


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
        logger.error(f"Redis error getting current Spotify track: {str(redis_err)}")
        raise HTTPException(status_code=500, detail=f"Redis Error")

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
        logger.error(f"Redis error stopping spotihue: {redis_err}")
        raise HTTPException(status_code=500, detail=f"Redis Error")
    except celery.exceptions.CeleryError as celery_err:
        logger.error(f"Celery error starting spotihue: {celery_err}")
        raise HTTPException(status_code=500, detail=f"Celery Error")
    except Exception as e:
        logger.error(f"Error starting spotihue: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error")

    return response
