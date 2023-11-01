from contextlib import contextmanager
from functools import wraps
import logging
import random
import time
from typing import Generator, List

from celery.app import task
from phue import PhueException
from redis import Redis
from spotipy.oauth2 import SpotifyOauthError

from . import celery_app, constants, oauth, redis_client, spotihue

logger = logging.getLogger(__name__)


class SingletonTask(task.Task):

    @staticmethod
    def run_singleton_task(bound_task_function):
        """Meant to decorate a bound celery task function such that there can only be 1 instance of the
            task running at any given point.
            Ex:

            @celery_app.task(base=SingletonTask, bind=True)
            @run_singleton_task
            def my_celery_task(self, other_param):
                pass

        Args:
            bound_task_function (Callable): a celery task function which is bound (ie. receives itself
                as its 1st argument).

        Returns:

        """
        @wraps(bound_task_function)
        def wrapper(*args, **kwargs):
            myself = args[0]
            my_task_name = myself.name
            my_task_id = myself.request.id

            my_task_lock = SingletonTaskLock(lock_id=myself.name, redis=redis_client)

            with my_task_lock.acquire_for(my_task_id) as acquired:
                if acquired is True:
                    logger.info(f'Acquired lock for {my_task_name}; running task {my_task_id}')
                    return bound_task_function(*args, **kwargs)
                else:
                    logger.info(f'Another {my_task_name} task is already being invoked; exiting task {my_task_id}')

        return wrapper


class SingletonTaskLock:
    """
    lock_id (key) = task name.
    lock values = task IDs.
    """
    LOCK_MAX_DURATION_SECONDS = 60 * 5  # 5 minutes

    def __init__(self, lock_id: str, redis: Redis):
        self.lock_id = lock_id
        self.redis = redis

    @contextmanager
    def acquire_for(self, task_id: str) -> Generator[str, None, None]:
        """Acquires simple Redis lock for a "singleton" celery task with ID task_id.

        Args:
            task_id (str): ID of a celery task that worker is trying to run.

        Returns:
            Generator[str, None, None]: context manager to get lock acquisition status for task,
                then subsequently relinquish that acquired lock (assuming the initial acquisition
                was successful).
        """
        lock = self.redis.get(self.lock_id)
        lock_acquired = bool(lock is None or (isinstance(lock, bytes) and lock.decode('utf-8') == task_id))

        try:
            if lock_acquired:
                self.redis.setex(self.lock_id, self.LOCK_MAX_DURATION_SECONDS, task_id)
            yield lock_acquired
        finally:
            if lock_acquired:
                self.redis.delete(self.lock_id)


def is_spotihue_running() -> bool:
    """Queries for the SpotiHue task by its cached spotihue_task_id. There should only be one
    run_spotihue task running at any given time.

    Returns:
         bool: Whether the SpotiHue (run_spotihue) task is running.
    """
    celery_inspect = celery_app.control.inspect()
    spotihue_task_id = redis_client.get(constants.REDIS_SPOTIHUE_TASK_ID)

    if spotihue_task_id:
        spotihue_task_id = spotihue_task_id.decode('utf-8')

        task_query_result = celery_inspect.query_task(*[spotihue_task_id, ])
        celery_host = list(task_query_result.keys())[0]  # we are only using the single celery worker

        if task_query_result[celery_host].get(spotihue_task_id) is not None:
            return True

    return False


@celery_app.task
def clear_spotihue_task_id(*args, **kwargs):
    logger.info('Clearing spotihue_task_id')
    redis_client.delete(constants.REDIS_SPOTIHUE_TASK_ID)


@celery_app.task
def run_spotihue(lights: List[str], current_track_retries: int = 0) -> None:
    logger.info("Running spotihue")
    spotihue.change_all_lights_to_normal_color(lights)

    retries_spent = 0
    retry_wait_seconds = 5

    while True:
        track_info = spotihue.retrieve_current_track_information(supply_defaults=False)

        # if user's Spotify has no current track (playing or paused), we wait to get a current track
        # current_track_retries-many times.
        if not track_info:
            if retries_spent < current_track_retries:
                retries_spent += 1
                logger.info(f'No currently-playing track on Spotify; trying again in {retry_wait_seconds} seconds')
                time.sleep(retry_wait_seconds)
                continue
            else:
                logger.info('No currently-playing track on Spotify; exiting')
                break  # task over.

        track_album_artwork_url = track_info["track_album_artwork_url"]

        last_track_info = redis_client.hgetall(constants.REDIS_TRACK_INFORMATION_KEY)
        last_track_album_artwork_url = last_track_info.get(b"track_album_artwork_url")

        if last_track_album_artwork_url:
            last_track_album_artwork_url = last_track_album_artwork_url.decode("utf-8")

        redis_client.hset(
            constants.REDIS_TRACK_INFORMATION_KEY,
            mapping=track_info
        )

        if last_track_album_artwork_url != track_album_artwork_url:
            logger.info("Syncing lights")
            spotihue.sync_lights_music(track_album_artwork_url, lights)

        sleep_duration = random.uniform(2, 4)
        time.sleep(sleep_duration)


@celery_app.task(base=SingletonTask, bind=True)
@SingletonTask.run_singleton_task
def setup_hue(self, backoff_seconds: int = 5, retries: int = 5) -> None:
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


@celery_app.task(base=SingletonTask, bind=True, throws=(oauth.SpotifyOauthSocketTimeout,))
@SingletonTask.run_singleton_task
def listen_for_spotify_redirect(self) -> None:
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
