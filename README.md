# aio_tiny_healthcheck
[![PyPI](https://img.shields.io/pypi/v/aio_tiny_healthcheck.svg)](https://github.com/nabrosimoff/aio_tiny_healthcheck)
[![Build Status](https://travis-ci.org/nabrosimoff/aio_tiny_healthcheck.svg?branch=master)](https://travis-ci.org/nabrosimoff/aio_tiny_healthcheck)
[![Build Status](https://travis-ci.org/nabrosimoff/aio_tiny_healthcheck.svg?branch=develop)](https://travis-ci.org/nabrosimoff/aio_tiny_healthcheck)

Tiny asynchronous implementation of healthcheck provider and server

# Installation

```bash
pip install aio-tiny-healthcheck
```

# Usage
By default, the Checker returns 200 if all checks successfully finish or 500 in opposite case.

## Using with aiohttp
```python
from aiohttp import web

from aio_tiny_healthcheck.checker import Checker

def some_sync_check():
    return True

async def some_async_check():
    return False

healthcheck_provider = Checker()
healthcheck_provider.add_check('sync_check_true', some_async_check)
healthcheck_provider.add_check('async_check_false', some_async_check)


app = web.Application()
app.router.add_get('/healthcheck', healthcheck_provider.aiohttp_handler)
web.run_app(app)
```

## Using with Sanic
```python
from sanic import Sanic
from sanic.response import json
from aio_tiny_healthcheck.checker import Checker

app = Sanic()

def some_sync_check():
    return True

async def some_async_check():
    return False

healthcheck_provider = Checker(success_code=201, fail_code=400)
healthcheck_provider.add_check('sync_check_true', some_async_check)
healthcheck_provider.add_check('async_check_false', some_async_check)

@app.route("/healthcheck")
async def test(request):
    hc_response = healthcheck_provider.check_handler()
    return json(hc_response.body, status=hc_response.code)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

## Using in concurrent mode
You should want to run healthcheck in background if you already have some blocking operation in your execution flow.
So, you can just use built-in server for this.

```python 
from aio_tiny_healthcheck.checker import Checker
from aio_tiny_healthcheck.http_server import HttpServer
import asyncio


async def some_long_task():
    await asyncio.sleep(3600)


def some_sync_check():
    return True


async def some_async_check():
    return True


aio_thc = Checker()
hc_server = HttpServer(
    aio_thc,
    path='/health',
    host='localhost',
    port=9090
)

aio_thc.add_check('sync_check_true', some_async_check)
aio_thc.add_check('async_check_false', some_async_check)


async def main():
    # Run healthcheck concurrently
    asyncio.create_task(hc_server.run())

    # Run long task
    await some_long_task()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

```

## Utility for health checking

```
python -m aio_tiny_healthcheck http://localhost:9192/healthcheck
```

Useful for running health check without external dependencies like curl.

By default, concurrent server and health checking utility are working
with a port and query path `http://localhost:8000/healthcheck`.
So, if you run concurrent server with no using arguments, you can also run the utility
with without arguments `python -m aio_tiny_healthcheck`.
