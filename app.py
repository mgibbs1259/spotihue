from flask import Flask, render_template, request

from spotihue import SpotiHue


app = Flask(__name__)

@app.route("/")
def spotihue_welcome():
    return render_template("spotihue_welcome.html")

@app.route("/connect", methods=["GET", "POST"])
def spotihue_connect():
    if request.method == "POST":
        if request.form["submit_button"] == "Yes":
            try:
                spotihue = SpotiHue()
                spotihue.connect_hue_bridge_first_time()
                return render_template("spotihue_main.html")
            except:
                return render_template("spotihue_welcome.html", message='Connection unsuccessful. Please press '
                                                                        'Hue Bridge button and click/press "Yes".')
    return render_template("spotihue_main.html")

@app.route("/play", methods=["GET", "POST"])
def spotihue_sync():
    if request.method == "POST":
        if request.form["submit_button"] == "SpotiHue":
            spotihue = SpotiHue()
            spotihue.sync_current_track_album_artwork_lights()
    return render_template("spotihue_main.html", message='SpotiHue was stopped. Turn on Spotify and '
                                                         'click/press "SpotiHue".')

if __name__ == "__main__":
    app.run()
