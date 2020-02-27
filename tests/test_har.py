#!/usr/bin/env python3

import asyncio
from unittest.mock import Mock

import pytest
from httpx import AsyncClient, Request, Response

from httpxhar import HarAsyncClient, __version__, to_curl


def test_version():
    assert __version__ == '0.1.0'


def test_to_curl():
    req = Request(
        method='PUT',
        url='https://example.com',
        params=[('key', 'value')],
        headers={'X-Curlx-Test': 'true'},
        json={'json_body': [{'key': 'value'}, 1]}
    )

    converted = to_curl(req, compressed=True, insecure=True)
    assert converted


def future(res) -> asyncio.Future:
    future = asyncio.Future()
    future.set_result(res)
    return future


@pytest.mark.asyncio
async def test_client():
    # Sad we don't have AsyncMock in py37

    req = Request(
        'PUT',
        url='https://testurl',
        params={'key': 'value', 'key1': 'value1', 'key1': 'value1'},
        headers={
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:73.0) '
                'Gecko/20100101 Firefox/73.0'
            ),
            'Accept': '*/*',
            'Accept-Language': 'en-US',
            'DNT': '1',
            'Connection': 'keep-alive',
            # 'Cookie': '-1145652274.cache-source=[%224.0k%20Stars%22%2C%22236%20Forks%22]',  # noqa
            'Referer': 'https://www.python-httpx.org/quickstart/',
            'If-Modified-Since': 'Wed, 19 Feb 2020 12:59:57 GMT',
            'If-None-Match': 'W/"5e4d314d-1c80"',
            'Cache-Control': 'max-age=0',
            'TE': 'Trailers',
        },
        cookies={
            '-1145652274.cache-source':
            '[%224.0k%20Stars%22%2C%22236%20Forks%22]'
        },
        json={'key': 'value', 'array': [1, 2, 3, None]},
    )

    mock_resp = Response(
        status_code=200,
        request=req,
        headers={
            'date': 'Thu, 27 Feb 2020 20:56:58 GMT',
            'via': '1.1 varnish',
            'cache-control': 'max-age=600',
            'etag': 'W/"5e4d314d-1c80"',
            'expires': 'Thu, 27 Feb 2020 21:05:29 GMT',
            'age': '2',
            'content-type': 'application/json; charset=UTF-8',
            'x-served-by': 'cache-lga21938-LGA',
            'x-cache': 'HIT',
            'x-cache-hits': '1',
            'x-timer': 'S1582837018.377474,VS0,VE0',
            'vary': 'Accept-Encoding',
            'x-fastly-request-id': '6b0f981c9359ed3fab1bbcf59aaf969d65fcf68b',
            'X-Firefox-Spdy': 'h2',
        },
        content=b'{"key": "value", "array": [1, 2, 3, None]}',
        # history=[Response(...)],
        http_version='HTTP/2',
    )
    async with HarAsyncClient(http2=True) as client:
        AsyncClient.send = Mock(return_value=future(mock_resp))
        resp = await client.send(request=req)
        assert AsyncClient.send.call_count == 1
        assert resp == mock_resp
