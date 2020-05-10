# smart-tv-telegram
A Telegram Bot to stream content on your smart TV (also Chromecast, FireTV and other UPnP device)

## Feature
- Streaming, the bot will not have to download the entire file before playing it on your device
- You can play anything if your device has the right codec
- You can streaming on any device that supports UPnP (AVTransport)
- Chromecast support
- Streaming over HTTP

Note: Chromecast (1st, 2nd and 3rd Gen.) [only supports H.264 and VP8 video codecs](https://developers.google.com/cast/docs/media#video_codecs)

Note: Most LG TVs with WebOS have an incorrect UPnP implementation, throw it in the trash and buy a new TV

## How-to setup
Make sure you have an updated version of python, only the latest version will be supported

(currently it also works on Python 3.6)

- Download the repository
- Install python dependencies from requirements.txt
- Copy config.json.example to config.json
- Edit config.ini

```bash
git clone https://github.com/andrew-ld/smart-tv-telegram
cd smart-tv-telegram
python3 -m pip install -r requirements.txt
cp config.ini.example config.ini
nano config.json
python3 .
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

**A:** Check the video bitrate, this bot supports maximum ~1.5Mb/s
