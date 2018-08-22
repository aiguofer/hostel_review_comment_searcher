# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date

from dateutil.relativedelta import relativedelta
from selenium import webdriver


from hostel_review_comment_searcher.models import Booking, HostelWorld, Google, Hostel
from hostel_review_comment_searcher.util import merge_results

session = None


def get_session():
    global session
    if session is None:
        options = webdriver.ChromeOptions()
        options.add_argument("headless")
        session = webdriver.Chrome(chrome_options=options)
    return session


def search(
    loc_query="cuenca, ecuador",
    guests=1,
    checkin=date.today() + relativedelta(days=1),
    days=1,
    min_match=80,
):
    session = get_session()
    booking = Booking(session)
    hostelworld = HostelWorld(session)
    google = Google(session)

    b_results = booking.search(loc_query, guests, checkin, days)
    hw_results = hostelworld.search(loc_query, guests, checkin, days)

    results = merge_results(hw_results, b_results, min_match)
    final = []
    for key in results.keys():
        result = results[key]
        hostel = {}
        google_info = google.get_hostel_info(key, loc_query)
        if google_info:
            hostel["google"] = google_info

        hw_url = result.get("hostelworld")
        if hw_url:
            hostel["hostelworld"] = hostelworld.get_hostel_info(hw_url)

        b_url = result.get("booking")
        if b_url:
            hostel["booking"] = booking.get_hostel_info(b_url)
        h = Hostel(session, hostel)
        # h.fetch_reviews()
        final.append(h)

    return sorted(final, key=lambda x: x.avg_rating, reverse=True)


def search_results(results, keyword, topn=10):
    res = results[: min(topn, len(results))]
    for result in res:
        if len(result.reviews) == 0:
            result.fetch_reviews()

    for ix, hostel in enumerate(sorted(res, key=lambda x: x.rating, reverse=True)):
        print(ix)
        print(hostel["name"])
        print(hostel["rating"])
        print(round(hostel.avg_rating, 2))
        print(round(hostel.rating, 2))
        print(hostel["url"])
        print(hostel["address"])
        print(
            "---------".join([x.__unicode__() for x in hostel.search_reviews(keyword)])
        )
        print("============================================")
        print("")
