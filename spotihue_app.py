from flask import Flask, render_template, request
from phue import Bridge
import spotipy.util as util
from spotipy import Spotify

import credentials
from spotihue import SpotiHue


app = Flask(__name__)


@app.route("/")
def spotihue_welcome():
    return render_template("spotihue_welcome.html")


@app.route("/connect/", methods=["GET", "POST"])
def spotihue_connection():
    if request.form["submit_button"] == "Yes":
        try:
            hue_bridge = Bridge(credentials.hue_bridge_ip_address)
            hue_bridge.connect()
            return render_template("spotihue_sync.html", hb_connection_message="Connection Successful")
        except:
            return render_template("spotihue_welcome.html", hb_connection_message="Connection Unsuccessful. "
                                                                                  "Please Press Hue Bridge Button "
                                                                                  "and Try Again.")
    else:
        return render_template("spotihue_sync.html", hb_connection_message="Connection Successful")


@app.route("/sync/", methods=["GET", "POST"])
def spotihue_sync():
    if request.form["submit_button"] == "Sync":
        hue_bridge = Bridge(credentials.hue_bridge_ip_address)
        spotify_token = util.prompt_for_user_token(credentials.spotify_username, credentials.spotify_scope,
                                                   credentials.spotify_client_id, credentials.spotify_client_secret,
                                                   credentials.spotify_redirect_uri)
        spotify = Spotify(auth=spotify_token)
        spotihue = SpotiHue(hue_bridge, spotify)
        spotihue.sync_current_track_album_artwork_lights()
        return render_template("spotihue_sync.html", hb_connection_message="Syncing Stopped. "
                                                                           "Turn Spotify On and Press Sync.")


if __name__ == "__main__":
    app.run()
