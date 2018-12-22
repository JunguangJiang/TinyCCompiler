import codecs

def parse_escape(s):
    return codecs.escape_decode(bytes(s, "ascii"))[0].decode("ascii")
