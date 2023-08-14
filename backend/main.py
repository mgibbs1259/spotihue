import os
import time
import random
import logging
from typing import Any, List, Union

import redis
import celery
import uvicorn
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException

from spotihue.spotihue import SpotiHue


class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Any = None


if os.path.exists(".env"):
    load_dotenv(".env")


spotihue = SpotiHue(
    os.environ.get("SPOTIFY_USERNAME"),
    os.environ.get("SPOTIFY_SCOPE"),
    os.environ.get("SPOTIFY_CLIENT_ID"),
    os.environ.get("SPOTIFY_CLIENT_SECRET"),
    os.environ.get("SPOTIFY_REDIRECT_URI"),
    os.environ.get("HUE_BRIDGE_IP_ADDRESS"),
)


redis_client = redis.Redis(host="redis", port=6379, db=0)
celery_app = celery.Celery("celery_app", broker="redis://redis:6379")
fast_app = FastAPI()


@celery_app.task
def run_spotihue(lights: List[str]) -> None:
    logging.info("Running spotihue")

    while spotihue.determine_current_track_status():
        last_track_info = redis_client.hgetall("current_track_information")
        last_track_album_artwork_url = last_track_info.get(b"track_album_artwork_url")
        if last_track_album_artwork_url:
            last_track_album_artwork_url = last_track_album_artwork_url.decode("utf-8")

        (
            track_name,
            track_artist,
            track_album,
            track_album_artwork_url,
        ) = spotihue.retrieve_current_track_information()

        redis_client.hmset(
            "current_track_information",
            {
                "track_name": track_name,
                "track_artist": track_artist,
                "track_album": track_album,
                "track_album_artwork_url": track_album_artwork_url,
            },
        )

        if last_track_album_artwork_url != track_album_artwork_url:
            logging.info("Syncing lights")
            spotihue.sync_lights_music(track_album_artwork_url, lights)

        sleep_duration = random.uniform(2, 4)
        time.sleep(sleep_duration)


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
        raise HTTPException(status_code=400, detail="Selected lights list is required")

    try:
        redis_client.set("lights", ",".join(lights))

        response = StandardResponse(
            success=True, message="Selected lights list stored in Redis"
        )

    except redis.exceptions.RedisError as redis_err:
        raise HTTPException(status_code=500, detail=f"Redis Error: {str(redis_err)}")

    return response


@fast_app.put("/start-spotihue")
async def start_spotihue(lights: List[str] = None):
    try:
        if not lights:
            # stored_lights = redis_client.get("lights")
            # if stored_lights:
            #     lights = stored_lights.split(",")
            # else:
            raise ValueError("Empty list of lights")

        spotihue_status = redis_client.get("spotihue")
        print(spotihue_status)
        # if spotihue_status:
        #     response = StandardResponse(
        #         success=True, message="spotihue is already running"
        #     )
        # else:
        spotihue.change_all_lights_to_normal_color(lights)

        task = run_spotihue.delay(lights)
        redis_client.set("spotihue", str(task.id))

        response = StandardResponse(success=True, message="spotihue started")

    except redis.exceptions.RedisError as redis_err:
        raise HTTPException(status_code=500, detail=f"Redis Error: {redis_err}")
    except celery.exceptions.CeleryError as celery_err:
        raise HTTPException(status_code=500, detail=f"Celery Error: {celery_err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

    return response


@fast_app.get("/current-track-information")
async def retrieve_current_track_information():
    try:
        track_info = redis_client.hgetall("current_track_information")

        response = StandardResponse(
            success=True,
            message="Current track information retrieved successfully",
            data=track_info,
        )

    except redis.exceptions.RedisError as redis_err:
        raise HTTPException(status_code=500, detail=f"Redis Error: {str(redis_err)}")

    return response


@fast_app.put("/stop-spotihue")
async def stop_spotihue(lights: List[str] = None):
    try:
        if not lights:
            stored_lights = redis_client.get("lights")
            if stored_lights:
                lights = stored_lights.split(",")
            else:
                raise ValueError("Empty list of lights")

        spotihue_status = redis_client.get("spotihue")
        if spotihue_status:
            celery_app.control.revoke(spotihue_status, terminate=True)
            spotihue.change_all_lights_to_normal_color(lights)
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


if __name__ == "__main__":
    uvicorn.run(fast_app, host="0.0.0.0", port=8000)
