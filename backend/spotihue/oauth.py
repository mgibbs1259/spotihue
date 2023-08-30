import logging
import webbrowser
from urllib import parse
from typing import Optional

from spotipy import oauth2, util


logger = logging.getLogger(__name__)


def start_local_http_server(port, handler=oauth2.RequestHandler):
    server = oauth2.HTTPServer(("0.0.0.0", port), handler)
    server.allow_reuse_address = True
    server.auth_code = None
    server.auth_token_form = None
    server.error = None
    return server


class SpotifyOauth(oauth2.SpotifyOAuth):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.auth_url = self.get_authorize_url(state=self.state)

    def _open_auth_url(self) -> None:
        """Opens Spotify user auth url in a new browser tab, if possible.

        Returns: None
        """
        try:
            success = webbrowser.open_new_tab(self.auth_url)
            if success:
                logger.info(f"Opened {self.auth_url} in your browser")
            else:
                raise webbrowser.Error()
        except webbrowser.Error:
            logger.error(
                f"Failed to open auth URL in your browser (likely because you're running this "
                f"in Docker) - please navigate here: {self.auth_url}"
            )

    def _get_auth_response_local_server(self, redirect_port: int, open_browser: Optional[bool] = False) -> str:
        """ Gets user auth response using a local server.

        Args:
            redirect_port (int): port for local redirect socket to listen on.

        Returns:
            str: auth code from Spotify.
        """
        server = start_local_http_server(redirect_port)
        logger.info(f'Listening on port {redirect_port} for Spotify callback...')

        if open_browser:
            self._open_auth_url()

        server.handle_request()
        logger.info(f'Callback received!')

        if self.state is not None and server.state != self.state:
            raise oauth2.SpotifyStateError(self.state, server.state)

        if server.auth_code is not None:
            return server.auth_code
        elif server.error is not None:
            raise oauth2.SpotifyOauthError(
                "Received error from OAuth server: {}".format(server.error)
            )
        else:
            raise oauth2.SpotifyOauthError(
                "Server listening on localhost has not been accessed"
            )

    def get_auth_response(self, open_browser: Optional[bool] = None) -> str:
        """Gets user authorization from Spotify (ie, an auth code that can be exchanged with Spotify
        for a refreshable access token).

        Args:
            open_browser (bool): Whether to try to open user's browser for them.

        Returns:
            str: auth code from Spotify.
        """

        redirect_info = parse.urlparse(self.redirect_uri)
        redirect_host, redirect_port = util.get_host_port(redirect_info.netloc)

        if open_browser is None:
            open_browser = self.open_browser

        if (
            redirect_host in ("127.0.0.1", "localhost")
            and redirect_info.scheme == "http"
            and redirect_port
        ):
            try:
                return self._get_auth_response_local_server(redirect_port, open_browser=open_browser)
            except oauth2.SpotifyOauthError as e:
                logger.error(str(e))
                raise
        else:
            warning_message = (
                "Interactively pasting your redirect url won't work if you are running this "
                "in Docker. Set backend/.env file SPOTIFY_REDIRECT_URL to a valid "
                "`http://localhost:<port>` formatted value."
            )
            logger.warning(warning_message)
            try:
                return self._get_auth_response_interactive(open_browser=open_browser)
            except EOFError as e:
                logger.error(str(e))
                raise oauth2.SpotifyOauthError(warning_message)
