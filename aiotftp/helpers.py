def set_result(fut, result):
    if not fut.done():
        fut.set_result(result)


def set_exception(fut, etc):
    if not fut.done():
        fut.set_exception(etc)
