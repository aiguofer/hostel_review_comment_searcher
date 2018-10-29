# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from flask import render_template, request

from . import app, sse
from .models import HostelSerializer
from .search import search_city


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/reviews")
def get_reviews():
    sse.publish({"message": "Hello!"}, type="greeting")
    return "Message sent!"


@app.route("/search")
def search_endpoint():
    for result in search_city(**request.args):
        data = HostelSerializer(result).data
        sse.publish(data, type="search_results")
    # session["results"] = results

    # sse.publish(
    #     [
    #         {
    #             "google": {"name": "Test G", "url": "https://test.com"},
    #             "hostelworld": {"name": "Test HW", "url": "https://test.com"},
    #             "booking": {"name": "Test B", "url": "https://test.com"},
    #         },
    #         {
    #             "google": {"name": "Test G 2", "url": "https://test.com"},
    #             "hostelworld": {"name": "Test HW 2", "url": "https://test.com"},
    #             "booking": {"name": "Test B 2", "url": "https://test.com"},
    #         },
    #     ],
    #     type="search_results",
    # )

    return "Search Results Sent"
