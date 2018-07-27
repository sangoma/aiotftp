from collections import namedtuple
import datetime
import logging
import os
import re

access_log = logging.getLogger('aiotftp.access')

KeyMethod = namedtuple('KeyMethod', 'key method')


class AccessLogger:
    LOG_FORMAT_MAP = {
        'a': 'remote_address',
        't': 'request_start_time',
        'P': 'process_id',
        'o': 'operation',
        'r': 'request',
        'b': 'response_size',
        'T': 'request_time',
        'Tf': 'request_time_frac',
        'D': 'request_time_micro',
    }

    LOG_FORMAT = '%a %t %o "%r" %b %T'
    FORMAT_RE = re.compile(r'%([atPorbD]|Tf?)')
    # FORMAT_RE = re.compile(r'%(\{([A-Za-z0-9\-_]+)\}([ie])|[atPrsbODor]|Tf?)')
    CLEANUP_RE = re.compile(r'(%[^s])')
    _FORMAT_CACHE = {}  # type: Dict[str, Tuple[str, List[KeyMethod]]]

    def __init__(self, logger, log_format=LOG_FORMAT):
        self.logger = logger
        self.log_format = log_format

        _compiled_format = AccessLogger._FORMAT_CACHE.get(log_format)
        if not _compiled_format:
            _compiled_format = self.compile_format(log_format)
            AccessLogger._FORMAT_CACHE[log_format] = _compiled_format

        self._log_format, self._methods = _compiled_format

    def compile_format(self, log_format):
        methods = list()

        for atom in self.FORMAT_RE.findall(log_format):
            format_key = self.LOG_FORMAT_MAP[atom[0]]
            m = getattr(AccessLogger, '_format_%s' % atom[0])
            methods.append(KeyMethod(format_key, m))

        log_format = self.FORMAT_RE.sub(r'%s', log_format)
        log_format = self.CLEANUP_RE.sub(r'%\1', log_format)
        return log_format, methods

    @staticmethod
    def _format_a(request, response, time):
        if request is None:
            return '-'
        ip = request.remote[0]
        return ip if ip is not None else '-'

    @staticmethod
    def _format_t(request, response, time):
        now = datetime.datetime.utcnow()
        start_time = now - datetime.timedelta(seconds=time)
        return start_time.strftime('[%d/%b/%Y:%H:%M:%S +0000]')

    @staticmethod
    def _format_P(request, response, time):
        return "<%s>" % os.getpid()

    @staticmethod
    def _format_o(request, response, time):
        if request is None:
            return '-'
        return request.method.name

    @staticmethod
    def _format_r(request, response, time):
        if request is None:
            return '-'
        return request.filename

    @staticmethod
    def _format_b(request, response, time):
        if not response:
            return '-'
        return response.length

    @staticmethod
    def _format_T(request, response, time):
        return round(time)

    @staticmethod
    def _format_Tf(request, response, time):
        return '%06f' % time

    @staticmethod
    def _format_D(request, response, time):
        return round(time * 1000000)

    def _format_line(self, request, response, time):
        return ((key, method(request, response, time))
                for key, method in self._methods)

    def log(self, request, response, time):
        try:
            fmt_info = self._format_line(request, response, time)

            values = list()
            extra = dict()
            for key, value in fmt_info:
                values.append(value)

                if key.__class__ is str:
                    extra[key] = value
                else:
                    k1, k2 = key
                    dct = extra.get(k1, {})
                    dct[k2] = value
                    extra[k1] = dct

            self.logger.info(self._log_format % tuple(values), extra=extra)
        except Exception:
            self.logger.exception("Error in logging")
