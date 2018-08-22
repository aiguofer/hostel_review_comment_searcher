# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import sys
import time
from builtins import str
from datetime import date

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from fuzzywuzzy import fuzz
from nltk.corpus import wordnet
from requests import Request, get

try:
    from hostel_review_comment_searcher.util import strip_url, starsort
except:
    from .util import strip_url, starsort


class Review:
    def __init__(self, comment, score, source):
        self.comment = comment.replace("\ub207", "").replace("\ub209", "").strip()
        self.score = score
        self.source = source

    def __repr__(self):
        if sys.version_info > (3,):
            return self.__unicode__()
        else:
            return self.__unicode__().encode("utf-8")

    def __unicode__(self):
        return """
Source: {0}
Score: {1}
Comment:
"{2}"
""".format(
            self.source, self.score, self.comment
        )


class Website:
    def __init__(self, session):
        self.session = session

    def get_page_dynamic(self, url, params={}, scroll=False):
        full_url = Request("GET", url, params=params).prepare().url
        self.session.get(full_url)
        html = self.session.page_source
        if scroll and hasattr(self, "scroll_to_bottom"):
            self.scroll_to_bottom()
            html = self.session.page_source
        return BeautifulSoup(html, "lxml")

    def get_page(self, url, params={}):
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36"
        }
        return BeautifulSoup(get(url, params, headers=headers).text, "lxml")


class Google(Website):
    key = ""

    def _get_place_id(self, name, location):
        url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"

        params = {
            "input": name + " " + location,
            "inputtype": "textquery",
            "key": self.key,
            "fields": "name,place_id",
        }
        candidates = get(url, params).json()["candidates"]

        if len(candidates) == 1:
            return candidates[0]["place_id"]
        elif len(candidates) > 1:
            return sorted(candidates, key=lambda x: fuzz.ratio(x["name"], name))[-1][
                "place_id"
            ]

    def get_hostel_info_from_place_id(self, place_id):
        url = "https://maps.googleapis.com/maps/api/place/details/json"

        params = {
            "key": self.key,
            "place_id": place_id,
            "fields": "rating,name,url,formatted_address",
        }

        data = get(url, params).json()["result"]

        cid = re.match(".+cid=(.+)", data.get("url")).group(1)

        reviews_url = (
            "https://www.google.com/search?"
            "hl=en-US&q=Best+business+ever&ludocid={0}#lrd=0x0:{1},1"
        ).format(cid, hex(int(cid)).strip("L"))

        if data.get("rating") is not None:
            rating = data.get("rating") * 2.0
        else:
            rating = None

        return {
            "url": data.get("url"),
            "rating": rating,
            "number_of_ratings": self._get_number_of_ratings(reviews_url),
            "address": data.get("formatted_address"),
            "name": data.get("name"),
            "reviews_url": reviews_url,
        }

    def _get_number_of_ratings(self, reviews_url):
        try:
            page = self.get_page_dynamic(reviews_url, scroll=True)
            match = re.match(
                "(\d+).+",
                page.find("span", class_="fl").find("span").find("span").get_text(),
            )
            return int(match.group(1))
        except:
            pass

    def get_hostel_info(self, name, location):
        place_id = self._get_place_id(name, location)
        if not place_id:
            print("No results found for {0} in {1}".format(name, location))
            return
        return self.get_hostel_info_from_place_id(place_id)

    def get_hostel_reviews(self, reviews_url):
        page = self.get_page_dynamic(reviews_url, scroll=True)

        reviews = []
        for review in page.findAll(class_="gws-localreviews__google-review"):
            r = {"source": "Google", "comment": ""}
            for span in review.findAll("span"):
                if span.get("tabindex") or "review-full-text" in span.get("class", []):
                    r["comment"] = span.get_text()
                matches = re.match("(\d)/(\d)", span.get_text(strip=True))
                if matches:
                    r["score"] = float(matches.group(1))
                matches = re.match(".+(\d\.\d).+", span.get("aria-label", ""))
                if matches:
                    r["score"] = float(matches.group(1))
            if "score" in r:
                reviews.append(Review(**r))
        return reviews

    def scroll_to_bottom(self):
        SCROLL_PAUSE_TIME = 1

        for i in range(3):
            try:
                e = self.session.find_element_by_class_name("review-dialog-list")
                break
            except Exception:
                time.sleep(SCROLL_PAUSE_TIME)
                if i == 2:
                    print("Couldn't find Google reviews")
                return

        last_height = self.session.execute_script("return arguments[0].scrollHeight", e)

        self.session.execute_script(
            "arguments[0].scrollTop = arguments[0].scrollHeight", e
        )
        while True:
            time.sleep(SCROLL_PAUSE_TIME)

            self.session.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", e
            )

            new_height = self.session.execute_script(
                "return arguments[0].scrollHeight", e
            )
            if new_height == last_height:
                break
            last_height = new_height

        for link in self.session.find_elements_by_class_name("review-more-link"):
            if link.text:
                link.click()


class Booking(Website):
    host = "https://www.booking.com"

    def get_hostel_info(self, url):
        if self.host not in url:
            url = self.host + url

        page = self.get_page(url)
        return {
            "url": strip_url(url),
            "rating": self._get_rating(page),
            "number_of_ratings": self._get_number_of_ratings(page),
            "address": page.find(class_="hp_address_subtitle").get_text(strip=True),
            "name": page.find("h2", id="hp_hotel_name").get_text().strip(),
            "reviews_url": self._get_reviews_url(page),
        }

    def _get_reviews_url(self, page):
        try:
            return page.find(class_="show_all_reviews_btn")["href"]
        except:
            pass

    def _get_rating(self, page):
        try:
            return float(page.find(class_="review-score-badge").get_text())
        except Exception:
            pass

    def _get_number_of_ratings(self, page):
        text = page.find(class_="review-score-widget__subtext").get_text()
        return int("".join([c for c in text if str.isdigit(c)]))

    def _parse_reviews_page(self, reviews_page):
        reviews = reviews_page.find_all(class_="review_item_review")
        return [
            Review(
                (
                    (
                        "Positive - "
                        + (review.find(class_="review_pos").get_text().strip())
                        if review.find(class_="review_pos")
                        else ""
                    )
                    + "\n\n"
                    + (
                        "Negative - "
                        + (review.find(class_="review_neg").get_text().strip())
                        if review.find(class_="review_neg")
                        else ""
                    )
                ),
                float(
                    review.find(class_="review-score-badge")
                    .get_text()
                    .replace(",", ".")
                ),
                "Booking.com",
            )
            for review in reviews
        ]

    def get_hostel_reviews(self, reviews_url):
        reviews = []

        next_page = self.host + reviews_url
        while next_page:
            reviews_page = self.get_page_dynamic(next_page, {"r_lang": "all"})
            reviews.extend(self._parse_reviews_page(reviews_page))

            next_page = reviews_page.find(id="review_next_page_link")
            if next_page:
                next_page = self.host + next_page["href"]

        return reviews

    def search(
        self, loc_query, guests=1, checkin=date.today() + relativedelta(days=1), days=1
    ):
        params = {
            "nflt": "ht_id=203;ht_id=216;review_score=80;",  # ht_id=208;
            "ss": loc_query,
            "group_adults": guests,
            "checkin_year_month_monthday": checkin,
            "checkout_year_month_monthday": checkin + relativedelta(days=days),
        }
        page = self.get_page_dynamic(
            "https://www.booking.com/searchresults.en-gb.html", params
        )
        results = page.findAll(class_="hotel_name_link")

        next_page = page.find("a", class_="paging-next")

        while next_page:
            page = self.get_page_dynamic("https://www.booking.com/" + next_page["href"])
            results.extend(page.findAll(class_="hotel_name_link"))
            next_page = page.find("a", class_="paging-next")

        # need to strip the href because it has a leading \n
        return dict(
            (
                result.find(class_="sr-hotel__name").get_text(strip=True),
                strip_url(self.host + result["href"].strip()),
            )
            for result in results
        )


class HostelWorld(Website):
    def get_hostel_info(self, url):
        page = self.get_page_dynamic(url)
        return {
            "url": strip_url(url),
            "rating": self._get_rating(page),
            "number_of_ratings": self._get_number_of_ratings(page),
            "address": self._get_address(page),
            "name": page.find("h1", class_="main-title").get_text().strip(),
            "reviews_url": self._get_reviews_url(page),
        }

    def _get_reviews_url(self, page):
        try:
            return page.find("a", {"data-open": "reviews-overlay"})["href"]
        except Exception:
            pass

    def _get_rating(self, page):
        try:
            return float(page.find(class_="score").get_text())
        except Exception:
            pass

    def _get_number_of_ratings(self, page):
        for link in page.findAll("a", {"data-open": "reviews-overlay"}):
            text = link.get_text(strip=True)
            # there's multiple links on the page, find the first one that includes
            # the number of reviews
            try:
                return int("".join([c for c in text if str.isdigit(c)]))
            except Exception:
                pass

    def _get_address(self, page):
        addr = page.find(class_="address-line").get_text(strip=True).replace("\n", "")

        addr = re.sub("[ ]{2,}", " ", addr)
        addr = re.sub(" ?, ?", ",", addr)

        return addr.replace(",", ", ")

    def _parse_reviews(self, reviews_page):
        reviews = reviews_page.find_all(class_="reviewlisting")
        return [
            Review(
                review.find(class_="reviewtext").find("p").get_text(strip=True),
                float(review.find(class_="textrating").get_text()),
                "HostelWorld",
            )
            for review in reviews
        ]

    def get_hostel_reviews(self, reviews_url):
        reviews = []

        next_page = reviews_url
        while next_page:
            reviews_page = self.get_page(
                next_page, {"allLanguages": "true", "lang": "all"}
            )
            reviews.extend(self._parse_reviews(reviews_page))

            next_page = reviews_page.find("li", class_="pagination-next")
            if next_page:
                try:
                    next_page = next_page.find("a")["href"]
                except:
                    next_page = None

        return reviews

    def search(
        self, loc_query, guests=1, checkin=date.today() + relativedelta(days=1), days=1
    ):
        params = {
            "number_of_guests": guests,
            "date_from": checkin,
            "date_to": checkin + relativedelta(days=days),
            "search_keywords": loc_query,
            "ShowAll": 1,
        }

        page = self.get_page_dynamic("https://www.hostelworld.com/search", params)

        results = page.findAll(class_="resultheader")

        return dict(
            (
                result.find(class_="hwta-property-link").get_text(strip=True),
                strip_url(result.find(class_="hwta-property-link")["href"]),
            )
            for result in results
        )


class Hostel:
    def __init__(self, session, hostel_info):
        self.session = session
        self._data = hostel_info
        self._sites = {
            "google": Google(session),
            "booking": Booking(session),
            "hostelworld": HostelWorld(session),
        }

    def __getitem__(self, attr):
        if any(attr.startswith(key) for key in self._sites.keys()):
            parts = attr.split("_")
            return self._data.get(parts[0], {}).get(parts[1])
        else:
            return dict(
                (site, self._data[site].get(attr)) for site in self._data.keys()
            )

    @property
    def google(self):
        return self._data.get("google", {})

    @property
    def booking(self):
        return self._data.get("booking", {})

    @property
    def hostelworld(self):
        return self._data.get("hostelworld", {})

    @property
    def reviews(self):
        return (
            self.google.get("reviews", [])
            + self.booking.get("reviews", [])
            + self.hostelworld.get("reviews", [])
        )

    @property
    def rating(self):
        return starsort(self.reviews)

    @property
    def avg_rating(self):
        total = 0
        total_num_ratings = 0
        for key in self["rating"].keys():
            rating = self["rating"][key]
            num_ratings = self["number_of_ratings"][key]
            if rating is not None and num_ratings is not None:
                total += rating * num_ratings
                total_num_ratings += num_ratings

        if total_num_ratings > 0:
            return 1.0 * total / total_num_ratings

    def fetch_reviews(self):
        for key in self._data.keys():
            info = self._data[key]
            if info["reviews_url"] is not None:
                info["reviews"] = self._sites[key].get_hostel_reviews(
                    info["reviews_url"]
                )

    def search_reviews(self, query):
        return [
            review for review in self.reviews if query.lower() in review.comment.lower()
        ]
