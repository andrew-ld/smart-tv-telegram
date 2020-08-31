# smart-tv-telegram [![PyPI](https://img.shields.io/pypi/v/smart-tv-telegram)](https://pypi.org/project/smart-tv-telegram/) [![PyPI - License](https://img.shields.io/pypi/l/smart-tv-telegram)](https://github.com/andrew-ld/smart-tv-telegram/blob/master/LICENSE) [![Docker Cloud Build Status](https://img.shields.io/docker/cloud/build/andrewhyphenld/smart-tv-telegram)](https://hub.docker.com/r/andrewhyphenld/smart-tv-telegram)
A Telegram Bot to stream content on your smart TV (also Chromecast, FireTV and other UPnP device)

### Demonstration video
[![poc](https://i.ibb.co/ct8Qb3z/Screenshot-20200827-200637.png)](https://player.vimeo.com/video/452289383)


## Feature
- Streaming, the bot will not have to download the entire file before playing it on your device
- You can play anything if your device has the right codec
- You can streaming on any device that supports UPnP (AVTransport)
- Chromecast, Vlc (telnet api) and Kodi (xbmc http api) support
- Streaming over HTTP

Note: Chromecast (1st, 2nd and 3rd Gen.) [only supports H.264 and VP8 video codecs](https://developers.google.com/cast/docs/media#video_codecs)

Note: Most LG TVs with WebOS have an incorrect UPnP implementation, throw it in the trash and buy a new TV

## How-to setup
Make sure you have an updated version of python, only the latest version will be supported

(currently it also works on Python 3.6)

- Download the repository
- Install python dependencies from requirements.txt
- Copy config.ini.example to config.ini
- Edit config.ini

```bash
git clone https://github.com/andrew-ld/smart-tv-telegram
cd smart-tv-telegram
python3 setup.py sdist bdist_wheel
python3 -m pip install dist/*.whl
cp config.ini.example config.ini
nano config.ini
smart_tv_telegram -c config.ini -v 1
```

## How-to setup (Docker)
- Copy config.ini.example to config.ini
- Edit config.ini
- Build Docker
- Start Docker

```bash
cp config.ini.example config.ini
nano config.ini
docker image build -t smart-tv-telegram:latest .
docker run --network host -v "$(pwd)/config.ini:/app/config.ini:ro" -d smart-tv-telegram:latest
```

## Troubleshooting

**Q:** My Firewall block upnp and broadcasting, how can use kodi without it

**A:** Set `xbmc_enabled` to `1` and add your kodi device to `xbmc_devices` list

##
**Q:** What is the format of `xbmc_devices`

**A:** A List of Python Dict with `host`, `port`, (and optional: `username` and `password`)

**example:** `[{"host": "192.168.1.2", "port": 8080, "username": "pippo", "password": "pluto"}]`

##
**Q:** How-To control vlc from this bot

**A:** set `vlc_enabled` to `1` and add your vlc device to `vlc_devices` list

##
**Q:** What is the format of `vlc_devices`

**A:** A List of Python Dict with `host`, `port`, (and optional: `password`)

**example:** `[{"host": "127.0.0.1", "port": 4212, "password": "123"}]`


##
**Q:** How-To enable upnp on my device that use kodi

**A:** follow [this guide](https://kodi.wiki/view/Settings/Services/UPnP_DLNA) (you should enable remote control)

##
**Q:** How do I get a token?

**A:** From [@BotFather](https://telegram.me/BotFather)
##
**Q:** How do I set up admins?

**A:** You have to enter your user_id, there are many ways to get it, the easiest is to use [@getuseridbot](https://telegram.me/getuseridbot)
##
**Q:** How do I get an app_id and app_hash?

**A:** https://core.telegram.org/api/obtaining_api_id#obtaining-api-id
##
**Q:** The video keeps freezing

**A:** Check the video bitrate, this bot supports maximum ~4.5Mb/s
