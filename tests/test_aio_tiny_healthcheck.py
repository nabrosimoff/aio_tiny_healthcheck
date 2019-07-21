import pytest
from aio_tiny_healthcheck.aio_tiny_healthcheck import AioTinyHealthcheck
from aio_tiny_healthcheck.healthcheck_server_http import HealthcheckServerHttp
import json
import asyncio
import aiohttp

@pytest.fixture()
def check_class_object():
    class t:
        async def async_method_true(self):
            return True

        def sync_method_true(self):
            return True

    return t()

@pytest.fixture()
def sync_true():
    def f():
        return True
    return f


@pytest.fixture()
def sync_none():
    def f():
        return None
    return f


@pytest.fixture()
def sync_false():
    def f():
        return False
    return f


@pytest.fixture()
def async_true():
    async def f():
        return True
    return f


@pytest.fixture()
def async_false():
    async def f():
        return False
    return f


def test_add_check_sync(sync_true):
    aio_thc = AioTinyHealthcheck()

    aio_thc.add_check('sync', sync_true)

    assert 'sync' in aio_thc.sync_checks
    assert len(aio_thc.async_checks) == 0


def test_add_check_async(async_true):
    aio_thc = AioTinyHealthcheck()

    aio_thc.add_check('async', async_true)

    assert 'async' in aio_thc.async_checks
    assert len(aio_thc.sync_checks) == 0


def test_add_check_noncallable():
    aio_thc = AioTinyHealthcheck()

    with pytest.raises(TypeError):
        aio_thc.add_check('test', 'var')

def test_add_nonuniq_check_sync():

    aio_thc = AioTinyHealthcheck()

    aio_thc.add_check('sync', lambda:True)

    with pytest.raises(ValueError):
        aio_thc.add_check('sync', lambda:True)


def test_add_nonuniq_check_async():
    aio_thc = AioTinyHealthcheck()

    aio_thc.add_check('async', lambda: True)

    with pytest.raises(ValueError):
        aio_thc.add_check('async', lambda: True)


def test_add_sync_method(check_class_object):
    aio_thc = AioTinyHealthcheck()

    aio_thc.add_check('sync', check_class_object.sync_method_true)

    assert 'sync' in aio_thc.sync_checks
    assert len(aio_thc.async_checks) == 0


def test_add_async_method(check_class_object):
    aio_thc = AioTinyHealthcheck()

    aio_thc.add_check('async', check_class_object.async_method_true)

    assert 'async' in aio_thc.async_checks
    assert len(aio_thc.sync_checks) == 0


@pytest.mark.asyncio
async def test_check_handler_empty():
    aio_thc = AioTinyHealthcheck()

    result = await aio_thc.check_handler()

    assert result.code == 200
    assert len(result.body) == 0


@pytest.mark.asyncio
async def test_check_handler_none(sync_none):
    aio_thc = AioTinyHealthcheck()

    aio_thc.add_check('none', sync_none)

    with pytest.raises(TypeError):
        await aio_thc.check_handler()


@pytest.mark.asyncio
async def test_check_handler_sync_only(sync_true):
    aio_thc = AioTinyHealthcheck()

    aio_thc.add_check('sync_true', sync_true)
    result = await aio_thc.check_handler()

    assert result.code == 200
    assert result.body['sync_true'] == True


@pytest.mark.asyncio
async def test_check_handler_error(
        sync_true, sync_false, async_true, async_false
):
    aio_thc = AioTinyHealthcheck(fail_code=777)

    aio_thc.add_check('sync_true', sync_true)
    aio_thc.add_check('sync_false', sync_false)
    aio_thc.add_check('async_true', async_true)
    aio_thc.add_check('async_false', async_false)

    check_handler = await aio_thc.check_handler()

    assert check_handler.code == 777
    assert check_handler.body['sync_true'] is True
    assert check_handler.body['sync_false'] is False
    assert check_handler.body['async_true'] is True
    assert check_handler.body['async_false'] is False


@pytest.mark.asyncio
async def test_check_handler_success_aiohttp(async_true):
    aio_thc = AioTinyHealthcheck(success_code=201)

    aio_thc.add_check('async_true', async_true)

    response = await aio_thc.aiohttp_handler(None)

    assert response.status == 201
    assert json.loads(response.body.decode())['async_true'] == True


@pytest.mark.asyncio
async def test_healthcheck_server(sync_false):
    aio_thc = AioTinyHealthcheck()

    aio_thc.add_check('sync_false', sync_false)

    hc_server = HealthcheckServerHttp(aio_thc, host='localhost')

    task = asyncio.ensure_future(hc_server.run())

    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:8000/healthcheck/') as resp:
            assert resp.status == 500
            resp_body = await resp.text()
            print(resp_body)
            assert json.loads(resp_body)['sync_false'] == False


    hc_server.stop_later()
    await asyncio.sleep(1)
    task.cancel()

