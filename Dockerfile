FROM python:3

ENV PYTHONUNBUFFERED=1

WORKDIR /tmp/setup

COPY . .

RUN python3 setup.py sdist bdist_wheel

RUN python3 -m pip install --no-cache-dir dist/*.whl

WORKDIR /app

RUN rm -rf /tmp/setup

CMD ["smart_tv_telegram"]
