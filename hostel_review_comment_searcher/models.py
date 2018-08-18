# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import sys

from nltk.corpus import wordnet
from requests import get

from .util import get_page, get_page_dynamic, strip_url

google_key = "<put_your_key_here>"


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
        return 'Score: {0}\nComment: \n"{1}"'.format(self.score, self.comment)


class Hostel:
    host = ""
    _reviews = None
    google_rating = None
    google_url = None
    google_name = None
    google_address = None

    def __init__(self, url):
        if self.host not in url:
            url = self.host + url

        self.full_url = url
        self.page = get_page(self.url)

    @property
    def name(self):
        raise Exception("Must implement")

    @property
    def rating(self):
        raise Exception("Must implement")

    @property
    def url(self):
        raise Exception("Must implement")

    @property
    def reviews(self):
        if self._reviews is None:
            self.get_reviews()
        return self._reviews

    @property
    def avg_rating(self):
        if self.google_rating is not None:
            return (
                self.google_rating * 2.0 * self.google_ratings
                + self.rating * self.ratings
            ) / (1.0 + self.google_ratings + self.ratings)
        else:
            return self.rating

    def search_reviews(self, query):
        return [review for review in self.reviews if query.lower() in review.comment]

    def get_google_place_id(self):
        url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"

        params = {
            "input": self.name,
            "inputtype": "textquery",
            "key": google_key,
            "keywords": self.location,
            "fields": "name,place_id",
        }
        candidates = get(url, params).json()["candidates"]

        if len(candidates) == 1:
            return candidates[0]["place_id"]
        elif len(candidates) > 1:
            print(candidates)

    def augment_google_reviews(self):
        place_id = self.get_google_place_id()
        if not place_id:
            return
        url = "https://maps.googleapis.com/maps/api/place/details/json"

        params = {
            "key": google_key,
            "place_id": place_id,
            "fields": "rating,name,url,formatted_address",
        }

        data = get(url, params).json()["result"]
        self.google_url = data.get("url")
        self.google_rating = data.get("rating") * 2.0
        self.google_address = data.get("formatted_address")
        self.google_name = data.get("name")

        url = (
            "https://www.google.com/search?"
            "q=Best+business+ever&ludocid={0}#lrd=0x0:{1},1"
        )
        cid = re.match(".+cid=(.+)", self.google_url).group(1)
        req_url = url.format(cid, hex(int(cid)).strip("L"))

        page = get_page_dynamic(req_url, scroll=True)

        self.google_reviews = re.match(
            "(\d+).+",
            page.find("span", class_="fl").find("span").find("span").get_text(),
        )

        for reviews in page.findAll(class_="gws-localreviews__google-review"):
            r = {"source": "Google"}
            for span in reviews.findAll("span"):
                if span.get("tabindex"):
                    r["comment"] = span.get_text(strip=True)
                matches = re.match("(\d)/(\d)", span.get_text(strip=True))
                if matches:
                    r["score"] = float(matches.group(1))
                matches = re.match(".+(\d\.\d).+", span.get("aria-label", ""))
                if matches:
                    r["score"] = float(matches.group(1))
            if "score" not in r or "comment" not in r:
                print(reviews)
            else:
                self.reviews.append(Review(**r))
        return page

    # def augment_google_reviews(self):
    #     place_id = self.get_google_place_id()
    #     if place_id:
    #         url = "https://maps.googleapis.com/maps/api/place/details/json"

    #         params = {
    #             "key": google_key,
    #             "place_id": place_id,
    #             "fields": "rating,reviews,name,url",
    #         }

    #         data = get(url, params).json()["result"]
    #         self.google_url = data.get("url")
    #         self.google_rating = data.get("rating") * 2.0
    #         self.google_ratings = len(data.get("reviews", []))
    #         self.google_name = data.get("name")

    #         for review in data.get("reviews", []):
    #             self._reviews.append(
    #                 Review(review["text"], review["rating"] * 2.0, "Google")
    #             )


class BookingHostel(Hostel):
    host = "https://www.booking.com"

    @property
    def name(self):
        return self.page.find("h2", id="hp_hotel_name").get_text().strip()

    @property
    def rating(self):
        try:
            return float(self.page.find(class_="review-score-badge").get_text())
        except Exception:
            pass

    @property
    def location(self):
        return self.page.find(class_="hp_address_subtitle").get_text(strip=True)

    @property
    def url(self):
        return strip_url(self.full_url)

    @property
    def ratings(self):
        return int(
            "".join(
                [
                    c
                    for c in self.page.find(
                        class_="review-score-widget__subtext"
                    ).get_text()
                    if str.isdigit(c)
                ]
            )
        )

    def _parse_reviews(self, reviews_page):
        print("parsing page")
        reviews = reviews_page.find_all(class_="review_item_review")
        return [
            Review(
                (
                    (
                        "Positive: "
                        + (review.find(class_="review_pos").get_text().strip())
                        if review.find(class_="review_pos")
                        else ""
                    )
                    + "\n"
                    + (
                        "Negative: "
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

    def get_reviews(self):
        self._reviews = []
        next_page = self.page.find(class_="show_all_reviews_btn")

        while next_page:
            url = self.host + next_page["href"]
            reviews_page = get_page_dynamic(url, {"r_lang": "all"})
            self._reviews.extend(self._parse_reviews(reviews_page))

            next_page = reviews_page.find(id="review_next_page_link")

        # self.augment_google_reviews()
        return reviews_page


class HostelWorldHostel(Hostel):
    host = "https://www.hostelworld.com/"

    @property
    def name(self):
        return self.page.find("h1", class_="main-title").get_text().strip()

    @property
    def rating(self):
        try:
            return float(self.page.find(class_="score").get_text())
        except Exception:
            pass

    @property
    def url(self):
        return strip_url(self.full_url)

    @property
    def location(self):
        addr = (
            self.page.find(class_="address-line").get_text(strip=True).replace("\n", "")
        )

        addr = re.sub("[ ]{2,}", " ", addr)
        addr = re.sub(" ?, ?", ",", addr)

        return addr.replace(",", ", ")

    def _parse_reviews(self, reviews_page):
        print("parsing page")
        reviews = reviews_page.find_all(class_="reviewlisting")
        return [
            Review(
                review.find(class_="reviewtext").find("p").get_text(strip=True),
                float(review.find(class_="textrating").get_text()),
                "HostelWorld",
            )
            for review in reviews
        ]

    def get_reviews(self):
        self._reviews = []
        next_page = self.page.find("a", {"data-open": "reviews-overlay"})

        while next_page:
            reviews_page = get_page(
                next_page["href"], {"allLanguages": "true", "lang": "all"}
            )
            self._reviews.extend(self._parse_reviews(reviews_page))

            next_page = reviews_page.find("li", class_="pagination-next")
            if next_page:
                next_page = next_page.find("a")

        self.augment_google_reviews()
