FROM python:3

WORKDIR /srv/
RUN git clone --depth=1 https://github.com/andrew-ld/smart-tv-telegram

WORKDIR /srv/smart-tv-telegram/
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /srv/smart-tv-telegram/src/
RUN python -OO -m compileall .

CMD [ "python", "." ]
