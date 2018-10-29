from __future__ import absolute_import, unicode_literals

from datetime import date

from dateutil.relativedelta import relativedelta

from . import app
from .models import Booking, Google, Hostel, HostelWorld
from .util import merge_results


def search_city(
    loc_query,
    guests=1,
    checkin=date.today() + relativedelta(days=1),
    nights=1,
    min_match=80,
):
    with app.app_context():
        if isinstance(loc_query, list):
            loc_query = loc_query[0]
        print("searching for " + loc_query)
        booking = Booking()
        hostelworld = HostelWorld()
        google = Google()

        b_results = booking.search(loc_query, guests, checkin, nights)
        hw_results = hostelworld.search(loc_query, guests, checkin, nights)

        city = loc_query.split(",")[0]
        results = merge_results(hw_results, b_results, city, min_match)

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
            h = Hostel(hostel)
            h.fetch_reviews()
            yield h
        print("finished searching")


def search_results(results, keyword, topn=10):
    with app.app_context():
        res = results[: min(topn, len(results))]
        for result in res:
            if len(result.reviews) == 0:
                result.fetch_reviews()

        for ix, hostel in enumerate(sorted(res, key=lambda x: x.rating, reverse=True)):
            print("Rankin: " + str(ix))
            print(hostel["name"])
            print(hostel["rating"])
            print(round(hostel.avg_rating, 2))
            print(round(hostel.rating, 2))
            print(hostel["number_of_ratings"])
            print(hostel["url"])
            print(hostel["address"])
            print(
                "\n---------\n".join(
                    [x.__unicode__() for x in hostel.search_reviews(keyword)]
                )
            )
            print("============================================")
            print("")
