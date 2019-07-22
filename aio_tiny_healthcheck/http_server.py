from aiohttp import web
import asyncio

from aio_tiny_healthcheck import Checker


__all__ = ['HttpServer']


class HttpServer:
    """
    Async server for running healthcheck in case
    when you do not want to block execution flow by web-server
    """
    def __init__(
        self,
        healthcheck_provider: Checker,
        host: str = '0.0.0.0',
        path: str = '/healthcheck',
        port: int = 8000
    ):
        """
        :param healthcheck_provider: Checker instance
        :param host: listened host
        :param path: URL path to healthcheck
        :param port: port
        """
        self._healthcheck_provider = healthcheck_provider
        self._host = host
        self._port = port
        self._path = path
        self._running = False
        self._user_stopped = True
        self._server = None

    async def _handler(self, request):
        path = request.path.rstrip('/')

        if path == self._path:
            response = await self._healthcheck_provider.aiohttp_handler(None)
        else:
            response = web.Response(body='404 Not Found', status=404)

        return response

    async def run(self):
        """
        Run healthcheck http-server.
        You can run this method concurrently.
        Example: ```asyncio.create_task(hc_server.run())```
        """
        if self._running is False:
            self._running = True
            self._user_stopped = False

            self._server = web.Server(self._handler)
            runner = web.ServerRunner(self._server)
            await runner.setup()
            site = web.TCPSite(runner, self._host, self._port)
            await site.start()

            while self._user_stopped is False:
                await asyncio.sleep(0.1)

            await self._server.shutdown()
            self._running = False
        else:
            raise RuntimeError('Can not run healthcheck server twice')

    def stop_later(self):
        """
        Stop running the server
        """
        self._user_stopped = False

