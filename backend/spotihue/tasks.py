import logging
import random
import time
from typing import List

from phue import PhueException
from spotipy.oauth2 import SpotifyOauthError

from . import celery_app, constants, redis_client, spotihue

logger = logging.getLogger(__name__)


@celery_app.task
def run_spotihue(lights: List[str]) -> None:
    logger.info("Running spotihue")
    spotihue.change_all_lights_to_normal_color(lights)

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
            logger.info("Syncing lights")
            spotihue.sync_lights_music(track_album_artwork_url, lights)

        sleep_duration = random.uniform(2, 4)
        time.sleep(sleep_duration)


@celery_app.task
def setup_hue(backoff_seconds: int = 5, retries: int = 5) -> None:
    logger.info('Attempting to connect to Hue bridge...')

    for attempt in range(retries):
        try:
            time.sleep(backoff_seconds)
            _ = spotihue.hue_ready(raise_exception=True)
            logger.info('Hue connection set up!')
            break
        except PhueException as e:
            message = f'Attempt {attempt+1} unsuccessful: \'{e.message}\''
            if attempt < (retries - 1):
                logger.info(message)
                logger.info('Trying again...')
            else:
                logger.error(message)
                raise


@celery_app.task
def listen_for_spotify_redirect() -> None:
    logger.info(f'Waiting to receive user authorization from Spotify...')
    spotify_oauth = spotihue.spotify_oauth

    try:
        auth_code = spotify_oauth.get_auth_response()
        logger.info('Received user authorization from Spotify')
        spotify_oauth.get_access_token(code=auth_code, check_cache=False)
        logger.info('Cached access token from Spotify')
    except SpotifyOauthError as e:
        logger.error(str(e))
        raise
