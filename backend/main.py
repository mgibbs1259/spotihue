import os
from typing import Any, List, Union

# import redis
# import celery
import uvicorn
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException

from spotihue.spotihue import SpotiHue


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


# redis_client = redis.Redis(host="localhost", port=6379, db=0)
# celery_app = celery.Celery("spotihue", broker="redis://localhost:6379/0")
fast_app = FastAPI()


class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Any = None


# @celery_app.task
# def run_spotihue():
#     return spotihue.sync_lights_music()


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
            response = StandardResponse(success=False, message="No available lights")

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")


# @app.post("/selected-lights")
# def store_selected_lights(lights: List[str]):
#     try:
#         if not lights:
#             raise HTTPException(status_code=400, detail="Selected lights list is required")

#         # Store the list of lights in Redis with an 8-hour TTL (28800 seconds)
#         redis_client.setex("lights", 28800, ",".join(lights))

#         return StandardResponse(success=True, message="Selected lights list stored in Redis")

#     except redis.RedisError as redis_error:
#         raise HTTPException(status_code=500, detail=f"Redis Error: {str(redis_error)}")


@fast_app.put("/test/")
async def start_spotihue(lights: List[str]):
    spotihue.change_all_lights_to_normal_color(lights)
    spotihue.sync_lights_music(lights)
    return StandardResponse(success=True, message="spotihue started")


# @fastapp.get("/current-track-information/")
# async def retrieve_current_track_information():
#     # Get this from Redis for display purposes
#     pass


# @fast_app.put("/start-spotihue/")
# async def start_spotihue(lights: List[str]):
#     spotihue_status = redis_client.get("spotihue")

#     if spotihue_status:
#         raise HTTPException(status_code=400, detail="spotihue is already running")

#     spotihue.change_all_lights_to_normal_color(lights)
#     task = run_spotihue.delay()
#     redis_client.set("spotihue", task.id)

#     return StandardResponse(success=True, message="spotihue started")


# @fast_app.put("/stop-spotihue/")
# async def stop_spotihue():
#     spotihue_status = redis_client.get("spotihue")

#     if spotihue_status:
#         celery_app.control.revoke(spotihue_status.decode(), terminate=True)
#         redis_client.delete("spotihue")
#         spotihue.change_all_lights_to_normal_color(lights)
#         return StandardResponse(success=True, message="spotihue stopped")
#     else:
#         raise HTTPException(status_code=400, detail="spotihue is not running")


if __name__ == "__main__":
    uvicorn.run(fast_app, host="0.0.0.0", port=8000)
