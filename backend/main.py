import logging
from typing import Any, List

from celery import exceptions as celery_exceptions
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis

from spotihue import celery_app, constants, redis_client, spotihue, tasks

logger = logging.getLogger(__name__)


class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Any = None


fast_app = FastAPI()


@fast_app.get("/hue-ready")
def hue_setup_complete():
    hue_set_up = spotihue.hue_ready()
    return StandardResponse(success=True, message='Hue setup complete' if hue_set_up else 'Hue setup not complete',
                            data={'ready': hue_set_up})


@fast_app.post("/setup-hue")
def setup_hue():
    try:
        tasks.setup_hue.delay(retries=3)
    except Exception as e:
        logger.error(f'Error invoking Hue setup task: {e}')
        return StandardResponse(success=False, message='Error invoking Hue setup task', data={"setup_running": False})

    return StandardResponse(success=True, message='Hue setup task running', data={"setup_running": True})


@fast_app.get("/spotify-ready")
def spotify_authorization_complete():
    spotify_authorized = spotihue.spotify_ready()
    return StandardResponse(success=True, message='Authorized' if spotify_authorized else 'Not Authorized',
                            data={'ready': spotify_authorized})


@fast_app.get("/authorize-spotify")
def authorize_spotify():
    spotify_user_auth_url = spotihue.spotify_oauth.auth_url

    try:
        tasks.listen_for_spotify_redirect.delay()
    except celery_exceptions.CeleryError as celery_err:
        logger.error(f'Error invoking Spotify authorization task: {celery_err}')
        return StandardResponse(success=False, message='Error invoking Hue setup task', data={"setup_running": False})

    return StandardResponse(success=True, message='Paste this into a browser tab',
                            data={'auth_url': spotify_user_auth_url})


@fast_app.get("/available-lights")
async def retrieve_available_lights():
    try:
        available_lights = spotihue.retrieve_available_lights()
        data = {"lights": available_lights}

        if available_lights:
            response = StandardResponse(
                success=True,
                message="Available lights retrieved successfully",
                data=data,
            )
        else:
            response = StandardResponse(success=True, message="No available lights", data=data)

    except Exception as e:
        logger.error(f'Error retrieving available lights: {e}')
        raise HTTPException(status_code=500, detail=f"Internal Server Error")

    return response


@fast_app.post("/selected-lights")
def store_selected_lights(lights: List[str]):
    if not lights:
        raise HTTPException(status_code=400, detail='\"lights\" list is required.')

    try:
        redis_client.set(constants.REDIS_SELECTED_LIGHTS_KEY, ",".join(lights))

        return StandardResponse(
            success=True, message="Selected lights list stored in Redis"
        )

    except redis.exceptions.RedisError as redis_err:
        logger.error(f'Redis error storing selected lights: {redis_err}')
        raise HTTPException(status_code=500, detail=f"Redis Error")


@fast_app.put("/start-spotihue")
async def start_spotihue(lights: List[str] = None):
    if not lights:
        raise HTTPException(status_code=400, detail='\"lights\" list is required.')

    available_lights = spotihue.retrieve_available_lights()
    lights = [light for light in lights if light in available_lights]

    try:
        # TODO: make this idempotent

        task = tasks.run_spotihue.delay(lights)
        redis_client.set("spotihue", str(task.id))

        return StandardResponse(success=True, message="spotihue started")

    except redis.exceptions.RedisError as redis_err:
        logger.error(f'Redis error starting spotihue: {redis_err}')
        raise HTTPException(status_code=500, detail=f"Redis Error")
    except celery_exceptions.CeleryError as celery_err:
        logger.error(f'Celery error starting spotihue: {celery_err}')
        raise HTTPException(status_code=500, detail=f"Celery Error")
    except Exception as e:
        logger.error(f'Error starting spotihue: {e}')
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
        logger.error(f'Redis error getting current Spotify track: {str(redis_err)}')
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
        logger.error(f'Redis error stopping spotihue: {redis_err}')
        raise HTTPException(status_code=500, detail=f"Redis Error")
    except celery_exceptions.CeleryError as celery_err:
        logger.error(f'Celery error starting spotihue: {celery_err}')
        raise HTTPException(status_code=500, detail=f"Celery Error")
    except Exception as e:
        logger.error(f'Error starting spotihue: {e}')
        raise HTTPException(status_code=500, detail=f"Internal Server Error")

    return response
