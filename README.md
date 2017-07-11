aiotftp
=======

## Why?

Because what the world really needed was asynchronous, dynamically
routable TFTP.

Seriously, though: it can be useful for testing, and the intended use-case
is keeping track of the requests our devices make while under test, and
be able to do such testing against potentially many devices simultaneously.

While it can be used for the usual use case of TFTP (moving files into or
out of some directory) it's also possible to provide arbitrary logic to
operate on a per-request basis to either

* provide a buffer to use as the response to a RRQ
* recieve a buffer to do whatever you care to after a WRQ complete

## Documentation?

Eventually. Hopefully.
