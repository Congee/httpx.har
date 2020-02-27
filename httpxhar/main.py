#!/usr/bin/env python3

from __future__ import annotations

import datetime as dt
import http.cookies
import json
import tempfile
import time
import urllib.parse
from http.cookiejar import Cookie
from pathlib import Path
from typing import Sequence

import httpx
from httpx import AsyncClient, Request, Response

from . import __version__


class String(str):
    def __init__(self, init=None):
        self.data = [init] if init else []

    def __add__(self, chars) -> String:
        self.data.append(chars)
        return self

    def __str__(self) -> str:
        return ' '.join(self.data)


def to_curl(request: Request, compressed=False, insecure=False) -> str:
    cmd = String('curl')

    cmd += f'--request {request.method}'

    for k, v in request.headers.items():
        cmd += f"--header '{k}: {v}'"

    cmd += f"""--data '{request.read().decode()}'"""

    if compressed:
        cmd += '--compressed'

    if insecure:
        cmd += '--insecure'

    cmd += f"'{request.url}'"

    return str(cmd)


class HarAsyncClient(AsyncClient):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._entries: Sequence[dict] = []

    @property
    def har(self) -> dict:
        '''https://w3c.github.io/web-performance/specs/HAR/Overview.html'''
        log = {
            'version': '1.2',
            'creator': {
                'name': 'Curlx',
                'version': __version__,
            },
            'browser': {
                'name': 'httpx',
                'version': httpx.__version__,
            },
            'entries': self._entries,
            # 'pages': [],
            # 'comment': str
        }
        return {'log': log}

    def save_har_sync(self, path=None) -> None:
        tmp = Path(tempfile.gettempdir()) / f'httpx.{int(time.time())}.har'
        with open(path or tmp, 'w+') as fp:
            json.dump(self.har, fp)

    async def send(self, request: Request, *args, **kwargs) -> Response:
        start = dt.datetime.now().astimezone().isoformat()
        response = await super().send(request, *args, **kwargs)
        self._entries.append({
            # 'pageref': 'page_0',
            'startedDateTime': start,
            'time': response.elapsed.microseconds,
            "request": map_request(request),
            "response": map_response(response),
            # "cache": {...},
            "timings": {},
            # "serverIPAddress": "10.0.0.1",
            # "connection": "52492",
            # "comment": ""
        })
        return response


def timestamp_to_iso8601(ts: int) -> str:
    return dt.datetime.fromtimestamp(ts).astimezone().isoformat()


def query_from_url(url: str) -> tuple:
    split = urllib.parse.urlsplit(str(url))
    tup = urllib.parse.parse_qsl(split.query)
    return nvp_from_iterbale(tup)


def cookies_from_request(request: Request) -> Sequence[dict]:
    cookie_str = request.headers.get('Cookie')
    sc = http.cookies.SimpleCookie(cookie_str)
    # not morsel.coded_value
    return [{'name': k, 'value': morsel.value} for k, morsel in sc.items()]


def nvp_from_iterbale(iterable) -> Sequence[dict]:
    return tuple({'name': k, 'value': v} for k, v in iterable)


def map_request(request: Request) -> dict:
    def eat_data():
        request.read()
        if not request.content:
            return

        params = []
        text = request.content.decode()
        mime_type = request.headers['content-type']
        if mime_type.startswith('application/x-www-form-urlencoded'):
            # TODO: bytes?
            params = nvp_from_iterbale(urllib.parse.parse_qsl(text))
        elif mime_type.startswith('application/json'):
            ...
        elif mime_type.startswith('multipart/form-data'):
            ...
        else:
            raise NotImplementedError

        return {
            'mimeType': mime_type,
            'params': params,
            'text': text,
        }

    return {
        'method': request.method,
        'url': str(request.url),
        'httpVersion': 'HTTP/1.1',
        'cookies': cookies_from_request(request),
        'headers': nvp_from_iterbale(request.headers.items()),
        'queryString': query_from_url(str(request.url)),
        'postData': eat_data(),
        'headersSize': -1,
        'bodySize': -1,
    }


def map_response(response: Response) -> dict:
    return {
        "status": response.status_code,
        "statusText": response.reason_phrase,
        "httpVersion": "HTTP/1.1",
        "cookies": [eat_cookie(c) for c in response.cookies.jar],
        'headers': nvp_from_iterbale(response.headers.items()),
        "content": {
            'size': len(response.content),
            # 'compression': 0,
            'mimeType': response.headers['content-type'],
            'text': response.text,
        },
        "redirectURL": "",
        "headersSize": -1,
        "bodySize": -1,
        # "comment": ""
    }


def eat_cookie(cookie: Cookie) -> dict:
    # Cookie cannot be converted to dict in an elegant and trivial way
    map = lambda exp: dt.datetime.fromtimestamp(exp).astimezone().isoformat()
    return {
        'version': cookie.version,
        'name': cookie.name,
        'value': cookie.value,
        'path': cookie.path,
        'domain': cookie.domain,
        'secure': cookie.secure,
        # no time zone specified. local to iso 8601.
        'expires': map(cookie.expires) if cookie.expires else cookie.expires,
        'comment': cookie.comment or '',
    }
