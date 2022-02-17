from collections import defaultdict
from hashlib import sha256
import random
import string
import json
import uuid
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
    return val_bytes, False

def flatten_list(l: list):
    return [flatten_list(e) if isinstance(e, list) else e for e in l]

def insert_after(e, e2):
    return [*e, e2] if isinstance(e, list) else [e, e2]

def user_id_for_room(uid: uuid.UUID, room_name: str):
    return sha256(uid.bytes + b":" + room_name.encode('utf-8')).hexdigest()
