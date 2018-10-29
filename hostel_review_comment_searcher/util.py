# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import math
import re
import time

from fuzzywuzzy import fuzz


def clean_name(name, city):
    clean_name = name.lower()
    clean_name = re.sub("hostel|hotel|bnb|b&b|hostal|" + city.lower(), "", clean_name)
    clean_name = clean_name.strip()
    return clean_name


def merge_results(hw_results={}, b_results={}, city="", min_match=80):
    same_name = []
    for hw_result_name in hw_results.keys():
        for b_result_name in b_results.keys():
            ratio = fuzz.ratio(
                clean_name(hw_result_name, city), clean_name(b_result_name, city)
            )
            if ratio > min_match:
                print("{0} - {1} : {2}".format(hw_result_name, b_result_name, ratio))
                print(
                    "{0} - {1} : {2}".format(
                        clean_name(hw_result_name, city),
                        clean_name(b_result_name, city),
                        ratio,
                    )
                )
                same_name.append((hw_result_name, b_result_name))

    mapping = dict(same_name)

    final = {}
    for key in hw_results.keys():
        record = final.get(key, {})
        record["hostelworld"] = hw_results[key]
        final[mapping.get(key, key)] = record

    for key in b_results.keys():
        record = final.get(key, {})
        record["booking"] = b_results[key]
        final[key] = record

    return final


def strip_url(url):
    return re.match("(https?://[^?]+)", url).group(0)


def mean(numbers):
    return float(sum(numbers)) / max(len(numbers), 1)


def starsort(reviews):
    """
    http://www.evanmiller.org/ranking-items-with-star-ratings.html
    """
    ns = [0.0 for _ in range(10)]

    for r in reviews:
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
