# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import math
import re
import time

from bs4 import BeautifulSoup

# from requests_html import HTMLSession
from requests import Request, get
from selenium import webdriver

url = "https://www.booking.com/hotel/es/green-river-hostel.en-gb.html"

google_key = "<put_your_key_here>"

options = webdriver.ChromeOptions()
options.add_argument("headless")
session = webdriver.Chrome(chrome_options=options)
# requests_session = HTMLSession()


# def get_page_dynamic_requests(url, params={}):
#     full_url = Request("GET", url, params=params).prepare().url
#     html = requests_session.get(full_url).html
#     html.render()
#     return BeautifulSoup(html.raw_html, "lxml")


def get_page_dynamic(url, params={}, scroll=False):
    full_url = Request("GET", url, params=params).prepare().url
    session.get(full_url)
    html = session.page_source
    if scroll:
        scroll_to_bottom()
        html = session.page_source
    return BeautifulSoup(html, "lxml")


def get_page(url, params={}):
    return BeautifulSoup(get(url, params).text, "lxml")


def strip_url(url):
    return re.match("(https?://[^?]+)", url).group(0)


def mean(numbers):
    return float(sum(numbers)) / max(len(numbers), 1)


def starsort(review):
    """
    http://www.evanmiller.org/ranking-items-with-star-ratings.html
    """
    ns = [0.0 for _ in range(10)]

    for r in review.reviews:
        ns[int(round(r.score, 0)) - 1] += 1.0

    ns.reverse()

    N = sum(ns)
    K = len(ns)
    s = list(range(K, 0, -1))
    s2 = [sk ** 2 for sk in s]
    z = 1.65

    def f(s, ns):
        N = sum(ns)
        K = len(ns)
        return sum(sk * (nk + 1) for sk, nk in zip(s, ns)) / (N + K)

    fsns = f(s, ns)
    return fsns - z * math.sqrt((f(s2, ns) - fsns ** 2) / (N + K + 1))


def search_comments(results, query):
    res = []
    for result in results:
        reviews = result.search_reviews(query)
        comment_score = mean([review.score for review in reviews])
        comments = [review.comment for review in reviews]
        if len(comments) > 0:
            res.append(result)
            print(
                """
                Hostel: {0}
                Rating: {1}
                Matched Comment Score: {2}
                Comments: {3}
                """.format(
                    result.name, result.rating, comment_score, "\n\n".join(comments)
                )
            )
            print()

    return res


def scroll_to_bottom():
    SCROLL_PAUSE_TIME = 1

    for i in range(3):
        try:
            e = session.find_element_by_class_name("review-dialog-list")
            break
        except Exception:
            if i == 2:
                raise Exception("Couldn't find reviews")

    # Get scroll height
    last_height = session.execute_script("return arguments[0].scrollHeight", e)

    session.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", e)
    while True:
        # Wait to load page
        time.sleep(SCROLL_PAUSE_TIME)

        # print('scrolling....')

        # Scroll down to bottom
        session.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", e)

        # Calculate new scroll height and compare with last scroll height
        new_height = session.execute_script("return arguments[0].scrollHeight", e)
        if new_height == last_height:
            break
        last_height = new_height
