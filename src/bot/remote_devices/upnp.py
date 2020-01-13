__version__ = "0.15"

# original source:
# https://github.com/cherezov/dlnap/blob/master/dlnap/dlnap.py


import re
import time
import socket
import select
import logging
import traceback

from contextlib import contextmanager
from urllib.request import urlopen


SSDP_GROUP = ("239.255.255.250", 1900)
URN_AVTransport = "urn:schemas-upnp-org:service:AVTransport:1"
URN_AVTransport_Fmt = "urn:schemas-upnp-org:service:AVTransport:{}"

URN_RenderingControl = "urn:schemas-upnp-org:service:RenderingControl:1"
URN_RenderingControl_Fmt = "urn:schemas-upnp-org:service:RenderingControl:{}"

SSDP_ALL = "ssdp:all"


def _get_tag_value(x, i=0):
    x = x.strip()
    value = ''
    tag = ''

    # skip <? > tag
    if x[i:].startswith('<?'):
        i += 2
        while i < len(x) and x[i] != '<':
            i += 1

    # check for empty tag like '</tag>'
    if x[i:].startswith('</'):
        i += 2
        in_attr = False
        while i < len(x) and x[i] != '>':
            if x[i] == ' ':
                in_attr = True
            if not in_attr:
                tag += x[i]
            i += 1
        return tag.strip(), '', x[i + 1:]

    # not an xml, treat like a value
    if not x[i:].startswith('<'):
        return '', x[i:], ''

    i += 1  # <

    # read first open tag
    in_attr = False
    while i < len(x) and x[i] != '>':
        # get rid of attributes
        if x[i] == ' ':
            in_attr = True
        if not in_attr:
            tag += x[i]
        i += 1

    i += 1  # >

    # replace self-closing <tag/> by <tag>None</tag>
    empty_elmt = '<' + tag + ' />'
    closed_elmt = '<' + tag + '>None</' + tag + '>'

    if x.startswith(empty_elmt):
        x = x.replace(empty_elmt, closed_elmt)

    while i < len(x):
        value += x[i]
        if x[i] == '>' and value.endswith('</' + tag + '>'):
            # Note: will not work with xml like <a> <a></a> </a>
            close_tag_len = len(tag) + 2  # />
            value = value[:-close_tag_len]
            break
        i += 1

    return tag.strip(), value[:-1], x[i + 1:]


def _xml2dict(s, ignore_until_xml=False):
    if ignore_until_xml:
        s = ''.join(re.findall(".*?(<.*)", s, re.M))

    d = {}

    while s:
        tag, value, s = _get_tag_value(s)
        value = value.strip()
        is_xml, dummy, dummy2 = _get_tag_value(value)

        if tag not in d:
            d[tag] = []

        if not is_xml:
            if not value:
                continue
            d[tag].append(value.strip())

        else:
            if tag not in d:
                d[tag] = []
            d[tag].append(_xml2dict(value))

    return d


def _xpath(d, path):
    for p in path.split('/'):
        tag_attr = p.split('@')
        tag = tag_attr[0]

        if tag not in d:
            return None

        attr = tag_attr[1] if len(tag_attr) > 1 else ''

        if attr:
            a, val = attr.split('=')

            for s in d[tag]:
                if s[a] == [val]:
                    d = s
                    break
        else:
            d = d[tag][0]

    return d


def _get_port(location):
    port = re.findall(r'http://.*?:(\d+).*', location)
    return int(port[0]) if port else 80


def _get_control_url(xml, urn):
    return _xpath(
        xml, 'root/device/serviceList/service@serviceType={}/controlURL'.format(urn))


@contextmanager
def _send_udp(to, packet):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.sendto(packet.encode(), to)
    yield sock
    sock.close()


def _unescape_xml(xml):
    return xml.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')


# noinspection PyBroadException
def _send_tcp(to, payload):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.settimeout(5)
        sock.connect(to)
        sock.sendall(payload.encode('utf-8'))

        data = sock.recv(2048)
        data = data.decode('utf-8')
        data = _xml2dict(_unescape_xml(data), True)

        error_description = _xpath(
            data, 's:Envelope/s:Body/s:Fault/detail/UPnPError/errorDescription')

        if error_description is not None:
            logging.error(error_description)

    except:
        data = ''

    finally:
        sock.close()

    return data


def _get_location_url(raw):
    t = re.findall(r'\n(?i)location:\s*(.*)\r\s*', raw, re.M)
    if len(t) > 0:
        return t[0]
    return ''


def _get_friendly_name(xml):
    name = _xpath(xml, 'root/device/friendlyName')
    return name if name is not None else 'Unknown'


def _get_serve_ip(target_ip, target_port=80):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect((target_ip, target_port))
    my_ip = sock.getsockname()[0]
    sock.close()

    return my_ip


# noinspection PyMethodMayBeStatic
class DlnapDevice:
    # noinspection PyBroadException
    def __init__(self, raw, ip):
        self.__logger = logging.getLogger(self.__class__.__name__)
        self.__logger.info(
            '=> New DlnapDevice (ip = {}) initialization..'.format(ip))

        self.ip = ip
        self.ssdp_version = 1

        self.port = None
        self.name = 'Unknown'
        self.control_url = None
        self.rendering_control_url = None
        self.has_av_transport = False

        try:
            self.__raw = raw.decode()
            self.location = _get_location_url(self.__raw)
            self.__logger.info('location: {}'.format(self.location))

            self.port = _get_port(self.location)
            self.__logger.info('port: {}'.format(self.port))

            raw_desc_xml = urlopen(self.location).read().decode()

            self.__desc_xml = _xml2dict(raw_desc_xml)
            self.__logger.debug('description xml: {}'.format(self.__desc_xml))

            self.name = _get_friendly_name(self.__desc_xml)
            self.__logger.info('friendlyName: {}'.format(self.name))

            self.control_url = _get_control_url(
                self.__desc_xml, URN_AVTransport)
            self.__logger.info('control_url: {}'.format(self.control_url))

            self.rendering_control_url = _get_control_url(
                self.__desc_xml, URN_RenderingControl)
            self.__logger.info(
                'rendering_control_url: {}'.format(
                    self.rendering_control_url))

            self.has_av_transport = self.control_url is not None
            self.__logger.info('=> Initialization completed'.format(ip))

        except:
            self.__logger.warning(
                'DlnapDevice (ip = {}) init exception:\n{}'.format(
                    ip, traceback.format_exc()))

    def __repr__(self):
        return '{} @ {}'.format(self.name, self.ip)

    def __eq__(self, d):
        return self.name == d.name and self.ip == d.ip

    def _payload_from_template(self, action, data, urn):
        fields = ''
        for tag, value in data.items():
            fields += '<{tag}>{value}</{tag}>'.format(tag=tag, value=value)

        payload = """<?xml version="1.0" encoding="utf-8"?> <s:Envelope 
        xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" 
        s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"> <s:Body> <u:{action} xmlns:u="{urn}"> {fields} 
        </u:{action}> </s:Body> </s:Envelope>""".format(action=action, urn=urn, fields=fields)
        return payload

    def _create_packet(self, action, data):
        if action in ["SetVolume", "SetMute", "GetVolume"]:
            url = self.rendering_control_url
            urn = URN_RenderingControl_Fmt.format(self.ssdp_version)
        else:
            url = self.control_url
            urn = URN_AVTransport_Fmt.format(self.ssdp_version)
        payload = self._payload_from_template(
            action=action, data=data, urn=urn)

        packet = "\r\n".join([
            'POST {} HTTP/1.1'.format(url),
            'User-Agent: {}/{}'.format(__file__, __version__),
            'Accept: */*',
            'Content-Type: text/xml; charset="utf-8"',
            'HOST: {}:{}'.format(self.ip, self.port),
            'Content-Length: {}'.format(len(payload)),
            'SOAPACTION: "{}#{}"'.format(urn, action),
            'Connection: close',
            '',
            payload,
        ])

        self.__logger.debug(packet)
        return packet

    def set_current_media(self, url, instance_id=0):
        packet = self._create_packet('SetAVTransportURI',
                                     {'InstanceID': instance_id, 'CurrentURI': url, 'CurrentURIMetaData': ''})
        _send_tcp((self.ip, self.port), packet)

    def play(self, instance_id=0):
        packet = self._create_packet(
            'Play', {'InstanceID': instance_id, 'Speed': 1})
        _send_tcp((self.ip, self.port), packet)

    def pause(self, instance_id=0):
        packet = self._create_packet(
            'Pause', {'InstanceID': instance_id, 'Speed': 1})
        _send_tcp((self.ip, self.port), packet)

    def stop(self, instance_id=0):
        packet = self._create_packet(
            'Stop', {'InstanceID': instance_id, 'Speed': 1})
        _send_tcp((self.ip, self.port), packet)

    def seek(self, position, instance_id=0):
        packet = self._create_packet(
            'Seek', {'InstanceID': instance_id, 'Unit': 'REL_TIME', 'Target': position})
        _send_tcp((self.ip, self.port), packet)

    def volume(self, volume=10, instance_id=0):
        packet = self._create_packet('SetVolume',
                                     {'InstanceID': instance_id, 'DesiredVolume': volume, 'Channel': 'Master'})

        _send_tcp((self.ip, self.port), packet)

    def get_volume(self, instance_id=0):
        packet = self._create_packet(
            'GetVolume', {
                'InstanceID': instance_id, 'Channel': 'Master'})
        _send_tcp((self.ip, self.port), packet)

    def mute(self, instance_id=0):
        packet = self._create_packet(
            'SetMute', {
                'InstanceID': instance_id, 'DesiredMute': '1', 'Channel': 'Master'})
        _send_tcp((self.ip, self.port), packet)

    def unmute(self, instance_id=0):
        packet = self._create_packet(
            'SetMute', {
                'InstanceID': instance_id, 'DesiredMute': '0', 'Channel': 'Master'})
        _send_tcp((self.ip, self.port), packet)

    def info(self, instance_id=0):
        packet = self._create_packet(
            'GetTransportInfo', {
                'InstanceID': instance_id})
        return _send_tcp((self.ip, self.port), packet)

    def media_info(self, instance_id=0):
        packet = self._create_packet(
            'GetMediaInfo', {
                'InstanceID': instance_id})
        return _send_tcp((self.ip, self.port), packet)

    def position_info(self, instance_id=0):
        packet = self._create_packet(
            'GetPositionInfo', {
                'InstanceID': instance_id})
        return _send_tcp((self.ip, self.port), packet)

    def set_next(self, url):
        pass

    def next(self):
        pass


def discover(name='', ip='', timeout=1, st=SSDP_ALL, mx=3, ssdp_version=1):
    st = st.format(ssdp_version)

    payload = "\r\n".join([
        'M-SEARCH * HTTP/1.1',
        'User-Agent: {}/{}'.format(__file__, __version__),
        'HOST: {}:{}'.format(*SSDP_GROUP),
        'Accept: */*',
        'MAN: "ssdp:discover"',
        'ST: {}'.format(st),
        'MX: {}'.format(mx),
        '',
        ''])

    devices = []

    with _send_udp(SSDP_GROUP, payload) as sock:
        start = time.time()

        while True:
            if time.time() - start > timeout:
                # timed out
                break

            r, w, x = select.select([sock], [], [sock], 1)

            if sock in r:
                data, addr = sock.recvfrom(1024)
                if ip and addr[0] != ip:
                    continue

                d = DlnapDevice(data, addr[0])
                d.ssdp_version = ssdp_version

                if d not in devices:
                    if not name or name is None or name.lower() in d.name.lower():
                        if not ip:
                            devices.append(d)
                        elif d.has_av_transport:
                            # no need in further searching by ip
                            devices.append(d)
                            break

            elif sock in x:
                raise Exception('Getting response failed')

            else:
                # Nothing to read
                pass

    return devices


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(repr(discover('', '', 5, SSDP_ALL, 1)))
