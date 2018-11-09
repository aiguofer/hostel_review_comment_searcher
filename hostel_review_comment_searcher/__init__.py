# -*- coding: utf-8 -*-

"""Top-level package for Hostel Review Comment Searcher."""
from __future__ import absolute_import, unicode_literals

import os
import pickle
from json import JSONEncoder

from flask import Flask, g
from flask_sse import sse
from selenium import webdriver
from werkzeug.local import LocalProxy

from ._version import __version__, __version_info__

__all__ = [
    "__version__",
    "__version_info__",
    "__author__",
    "__email__",
    "app",
    "sse",
    "driver",
]

__author__ = """Diego Fernandez"""
__email__ = "aiguo.fernandez@gmail.com"

app = Flask(__name__)

app.config["REDIS_URL"] = os.environ.get("REDIS_URL", "redis://localhost")
app.register_blueprint(sse, url_prefix="/stream")

app.config.from_object(__name__)
app.config["ENV"] = "development"


def get_new_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(chrome_options=options)


def get_driver():
    if "driver" not in g:
        g.driver = get_new_driver()
    return g.driver


@app.teardown_appcontext
def teardown_driver(error):
    driver = g.pop("driver", None)

    if driver is not None:
        driver.close()


driver = LocalProxy(get_driver)


def _default(self, obj):
    return {"_python_object": pickle.dumps(obj).decode("latin1")}


JSONEncoder.default = _default
