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
- Edit config.json (`token`, `listen_host` with your local IP and `admin_id` with your user_id)

```bash
git clone https://github.com/andrew-ld/smart-tv-telegram
cd smart-tv-telegram
pip3 install -r requirements.txt
cd src
cp config.json.example config.json
nano config.json
```

## How-to setup (Docker)

- Download [Dockerfile](https://raw.githubusercontent.com/andrew-ld/smart-tv-telegram/master/Dockerfile) and [config.json.example](https://raw.githubusercontent.com/andrew-ld/smart-tv-telegram/master/src/config.json.example)
- Rename config.json.example to config.json
- Edit config.json (`token`, `listen_host` with your local IP and `admin_id` with your user_id)
- Set `"session_name": "sessions/smarttv"` in config.json (You can change the name as long as it matches the docker volume)
- Build Docker
- Start Docker

```bash
wget https://raw.githubusercontent.com/andrew-ld/smart-tv-telegram/master/Dockerfile
wget https://raw.githubusercontent.com/andrew-ld/smart-tv-telegram/master/src/config.json.example
mv config.json.example config.json
nano config.json
docker image build -t smart-tv-telegram:latest .
docker run --network host -v "$(pwd)/config.json:/srv/smart-tv-telegram/src/config.json:ro" -v "$(pwd)/sessions:/srv/smart-tv-telegram/src/sessions" -d smart-tv-telegram:latest
```

## Troubleshooting

**Q:** I'm having problems installing _cryptography_ with pip3, how can I install it?

**A:** Make sure you've installed [these dependencies](https://cryptography.io/en/latest/installation/#building-cryptography-on-linux)

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

**A:** Check the video bitrate, this bot supports maximum 2Mb/s
##
**Q:** The bot cannot find supported devices

**A:**
- Check if your router has UPnP enabled
- Try to enable workaround in config.json (This parameter requests all devices from the router instead of only devices with AVTransport)
- Check your firewall, in extreme case can try to reset iptables with `sudo iptables -F`
- Also make sure you have devices that support AVTransport with 

`gssdp-discover -t urn: schemas-upnp-org: service: AVTransport: 1` or `gssdp-discover`
