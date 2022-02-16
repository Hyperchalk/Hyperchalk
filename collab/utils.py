import random
import string
import json
import zlib
from typing import Optional, Tuple, Union

JSONType = Optional[Union[dict, list, str, int, float]]

def make_room_name(length):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

def load_content(content: bytes, compressed: bool = True) -> JSONType:
    if compressed:
        return json.loads(zlib.decompress(content).decode('utf-8'))
    return json.loads(content.decode('utf-8'))

def dump_content(content: JSONType, force_compression=False) -> Tuple[bytes, bool]:
    val_bytes = json.dumps(content, ensure_ascii=False).encode('utf-8')
    compressed = zlib.compress(val_bytes)
    if force_compression or len(compressed) < len(val_bytes):
        return compressed, True
    return val_bytes, True
