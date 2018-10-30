FROM joyzoursky/python-chromedriver:3.7
ENV REDIS_URL redis://redis:6379
ADD . /code
WORKDIR /code
RUN pip install -r requirements.txt && \
        adduser app
USER app
CMD gunicorn hostel_review_comment_searcher.routes:app --worker-class gevent --bind 0.0.0.0:$PORT
