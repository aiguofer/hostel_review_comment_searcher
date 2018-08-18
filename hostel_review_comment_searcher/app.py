# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date

from dateutil.relativedelta import relativedelta

from hostel_review_comment_searcher.models import BookingHostel, HostelWorldHostel
from hostel_review_comment_searcher.util import get_page_dynamic


def search(
    loc_query,
    guests=1,
    checkin=date.today(),
    checkout=date.today() + relativedelta(days=1),
):
    res = []
    res.extend(search_booking(loc_query, guests, checkin, checkout))
    res.extend(search_hostelworld(loc_query, guests, checkin, checkout))
    return res


def search_booking(
    loc_query,
    guests=1,
    checkin=date.today(),
    checkout=date.today() + relativedelta(days=1),
):
    params = {
        "nflt": "ht_id=203;ht_id=216;ht_id=208;review_score=80;",
        "ss": loc_query,
        "group_adults": guests,
        "checkin_year_month_monthday": checkin,
        "checkout_year_month_monthday": checkout,
    }
    page = get_page_dynamic("https://www.booking.com/searchresults.en-gb.html", params)
    results = page.findAll(class_="hotel_name_link")

    next_page = page.find("a", class_="paging-next")

    while next_page:
        page = get_page_dynamic("https://www.booking.com/" + next_page["href"])
        results.extend(page.findAll(class_="hotel_name_link"))
        next_page = page.find("a", class_="paging-next")

    # need to strip the href because it has a leading \n
    return [BookingHostel(result["href"].strip()) for result in results]


def search_hostelworld(
    loc_query,
    guests=1,
    checkin=date.today(),
    checkout=date.today() + relativedelta(days=1),
):
    params = {
        "number_of_guests": guests,
        "date_from": checkin,
        "date_to": checkout,
        "search_keywords": loc_query,
    }

    page = get_page_dynamic("https://www.hostelworld.com/search", params)

    results = page.findAll("a", class_="hwta-property-link")

    return [HostelWorldHostel(url) for url in set(result["href"] for result in results)]
