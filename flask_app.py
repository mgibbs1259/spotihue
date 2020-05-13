import uuid

from flask import Flask, session, render_template, request
from celery import Celery

from spotihue import SpotiHue


flask_app = Flask(__name__)

flask_app.config['SECRET_KEY'] = str(uuid.uuid4())

flask_app.config['CELERY_BROKER_URL'] = "redis://localhost:6379/0"
flask_app.config['CELERY_RESULT_BACKEND'] = "redis://localhost:6379/0"
flask_app.config['CELERY_TRACK_STARTED'] = True
flask_app.config['CELERY_SEND_EVENTS'] = True

celery = Celery(flask_app.name, broker=flask_app.config['CELERY_BROKER_URL'])
celery.conf.update(flask_app.config)

@celery.task()
def run_spotihue():
    return SpotiHue().sync_current_track_album_artwork_lights()

@flask_app.route("/")
def spotihue_welcome():
    return render_template("spotihue_welcome.html")

@flask_app.route("/connect", methods=["GET", "POST"])
def spotihue_connect():
    if request.method == "POST":
        if request.form["submit_button"] == "Yes":
            try:
                SpotiHue().connect_hue_bridge_first_time()
                return render_template("spotihue_main.html")
            except:
                return render_template("spotihue_welcome.html", message='Connection unsuccessful. Please press '
                                                                        'Hue Bridge button and click/press "Yes".')
    return render_template("spotihue_main.html")

@flask_app.route("/play", methods=["GET", "POST"])
def spotihue_play():
    if request.method == "POST":
        if request.form["submit_button"] == "SpotiHue":
            run_id = run_spotihue.delay()
            session["run_id"] = str(run_id)
            return render_template("spotihue_main.html", message="SpotiHue was started")

@flask_app.route("/stop", methods=["GET", "POST"])
def spotihue_stop():
    if request.method == "POST":
        if request.form["submit_button"] == "Stop SpotiHue":
            SpotiHue().change_light_color_normal()
            celery.control.revoke(session["run_id"], terminate=True)
            return render_template("spotihue_main.html", message='SpotiHue was stopped. Turn on Spotify and '
                                                                 'click/press "SpotiHue".')

if __name__ == "__main__":
    flask_app.run(debug=True)
