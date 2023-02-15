import msgpack
import datetime

TYPE_MARKER = '_t'
VALUE_FIELD = 'v'


def _enc(type_marker, value):
    return {TYPE_MARKER: type_marker, VALUE_FIELD: value}

def _dec(obj, type_key, function):
    if TYPE_MARKER in obj and obj[TYPE_MARKER] == type_key:
        try:
            return function(obj[VALUE_FIELD])
        except:
            raise ValueError(obj)
    return obj

def _encode(obj):
    if isinstance(obj, datetime.datetime):
        # Use bespoke instead of strptime because it breaks before 1900
        return _enc('d', f"{obj.year:04}{obj.month:02}{obj.day:02}{obj.hour:02}")
    return obj

def _decode(obj):
    # Use bespoke instead of strptime because it breaks before 1900
    obj = _dec(obj, 'd', lambda x: datetime.datetime(int(x[0:4]), int(x[4:6]), int(x[6:8]), int(x[8:10])))
    return obj

def dumps(data):
    return msgpack.packb(data, default=_encode)

def loads(serialdata):
    return msgpack.unpackb(serialdata, object_hook=_decode, strict_map_key=False)

def dump(data, f_obj):
    f_obj.write(dumps(data))

def load(f_obj):
    return loads(f_obj.read())
