import re
import typing

range_regex = re.compile(r"bytes=([0-9]+)-")


def parse_http_range(http_range: str, block_size: int) -> typing.Tuple[int, int]:
    matches = range_regex.search(http_range)

    if matches is None:
        raise ValueError()

    offset = matches.group(1)

    if not offset.isdigit():
        raise ValueError()

    offset = int(offset)
    safe_offset = (offset // block_size) * block_size
    data_to_skip = offset - safe_offset

    return safe_offset, data_to_skip
