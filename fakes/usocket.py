SOCK_STREAM = 1
SOCK_DGRAM = 2
AF_INET = 2
AF_INET6 = 10

def getaddrinfo(host, port, af=0, type=0, proto=0, flags=0):
    raise OSError("usocket not available in WASM")

def socket(*args, **kwargs):
    raise OSError("usocket not available in WASM")
