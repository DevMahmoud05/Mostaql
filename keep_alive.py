from flask import Flask
from threading import Thread
import logging


app = Flask(__name__)


@app.route('/')
def index():
    return {"msg": "Mostaql Channel running...."}


def run():
    try:
        app.run(host='0.0.0.0', port=8080)
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")


def keep_alive():
    t = Thread(target=run)
    t.start()
