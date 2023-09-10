import os

import celery
from dotenv import load_dotenv
import redis

from . import spotihue

if os.path.exists(".env"):
    load_dotenv(".env")

redis_client = redis.Redis(host="redis", port=6379, db=0)

spotihue = spotihue.SpotiHue(
    os.environ.get("SPOTIFY_SCOPE"),
    os.environ.get("SPOTIFY_CLIENT_ID"),
    os.environ.get("SPOTIFY_CLIENT_SECRET"),
    os.environ.get("SPOTIFY_REDIRECT_URI"),
    os.environ.get("HUE_BRIDGE_IP_ADDRESS"),
    redis_client=redis_client
)

celery_app = celery.Celery("celery_app", backend="redis://redis:6379", broker="redis://redis:6379")
