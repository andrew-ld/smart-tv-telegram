FROM python:3.13

ENV PYTHONUNBUFFERED=1

WORKDIR /tmp/setup

COPY . .

RUN python3 -m pip install setuptools

RUN python3 setup.py sdist bdist_wheel

RUN python3 -m pip install --no-cache-dir dist/*.whl

WORKDIR /app

RUN rm -rf /tmp/setup

HEALTHCHECK CMD ["smart_tv_telegram", "--healthcheck"]

CMD ["smart_tv_telegram"]
