def set_result(fut, result):
    if not fut.done():
        fut.set_result(result)


def set_exception(fut, etc):
    if not fut.done():
        fut.set_exception(etc)


def get_tid(addr):
    if len(addr) == 4 and addr[2:] != (0, 0):
        raise ValueError('Unsupported IPv6 address type: {}'.format(addr))
    return addr[:2]
