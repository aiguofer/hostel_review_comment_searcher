FROM joyzoursky/python-chromedriver:latest
ENV REDIS_URL redis://redis:6379
ADD . /code
WORKDIR /code
RUN apk add --virtual build-dependencies build-base gcc libxml2-dev libxslt-dev && \
        pip install --no-cache-dir -U setuptools pip && \
        pip install --no-cache-dir -r requirements.txt && \
        apk del build-dependencies && \
        adduser -D app
USER app
CMD gunicorn hostel_review_comment_searcher.routes:app --worker-class gevent --bind 0.0.0.0:$PORT
