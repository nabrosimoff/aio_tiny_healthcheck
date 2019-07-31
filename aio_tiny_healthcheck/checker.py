import asyncio
import functools
import inspect

from inspect import isfunction, ismethod
from typing import Union, Callable, Dict, Coroutine, Any


__all__ = ['Checker', 'HealthcheckResponse']

CheckResult = Dict[str, bool]


class HealthcheckResponse:
    def __init__(self, body: Union[CheckResult, None] = None, code: int = 200):
        self.body = body
        self.code = code


class Checker:
    def __init__(
            self,
            success_code: int = 200,
            fail_code: int = 500,
            timeout: int = 10
    ):
        """
        :param success_code: value of code if all checks finishes successful
        :param fail_code: value of code if at least
        one check finishes unsuccessful
        :param timeout: timeout of execution all of checks
        """

        self.__sync_healthchecks = set()
        self.__async_healthchecks = set()
        self.__success_code = success_code
        self.__fail_code = fail_code
        self.__timeout = timeout

    def add_check(
            self,
            name: str,
            check: Union[Callable[..., bool], Callable[..., Coroutine[Any, Any, bool]]]
    ):
        if iscoroutinefunction_or_partial(check) is True:
            if name not in self.checks:
                self.__async_healthchecks.add((name, check))
            else:
                raise ValueError('Check name must be unique')
        elif isfunction(check) is True or ismethod(check):
            if name not in self.checks:
                self.__sync_healthchecks.add((name, check))
            else:
                raise ValueError('Check name must be unique')
        else:
            raise (
                TypeError('Method expects argument "check" '
                          'of awaitable or callable object type. '
                          'Got <%s>' % (type(check))
                          )
            )

    @property
    def sync_checks(self):
        return tuple(name for (name, check) in self.__sync_healthchecks)

    @property
    def async_checks(self):
        return tuple(name for (name, check) in self.__async_healthchecks)

    @property
    def checks(self):
        return self.sync_checks + self.async_checks

    async def check_handler(self) -> HealthcheckResponse:
        if len(self.sync_checks) == 0 and len(self.async_checks) == 0:
            return HealthcheckResponse({}, self.__success_code)

        sync_checks_results = await self.__run_sync_checks()
        async_checks_results = await self.__run_async_checks()

        checks_results = {**sync_checks_results, **async_checks_results}

        self.__check_result_types(checks_results)

        if all(checks_results.values()) is True:
            code = self.__success_code
        else:
            code = self.__fail_code

        return HealthcheckResponse(checks_results, code)

    async def __run_async_checks(self) -> CheckResult:

        if len(self.async_checks) == 0:
            return {}

        async def wrapper(name: str, task: Callable):
            result = await task()
            return name, result

        async_check_tasks = {
            wrapper(name, check) for (name, check) in self.__async_healthchecks
        }

        done_checks, _ = await asyncio.wait(
            async_check_tasks,
            return_when=asyncio.ALL_COMPLETED
        )

        async_check_results = {t.result()[0]: t.result()[1] for t in done_checks}

        return async_check_results

    async def __run_sync_checks(self) -> CheckResult:
        loop = asyncio.get_event_loop()
        check_result = {}

        for (name, check) in self.__sync_healthchecks:
            result = await loop.run_in_executor(None, check)
            check_result[name] = result

        return check_result

    @staticmethod
    def __check_result_types(results: CheckResult):
        for name, status in results.items():
            if type(status) is not bool:
                raise TypeError(
                    'Healthcheck "%s" returning value type'
                    ' is "{%s}".'
                    'Required "bool".' % (
                        name, type(status)
                    )
                )
        return True

    async def aiohttp_handler(self, request):
        from aiohttp import web
        response = await self.check_handler()

        return web.json_response(response.body, status=response.code)


def iscoroutinefunction_or_partial(obj):
    """This function check if object is coroutine
    or coroutine with partial wrapper"""
    if isinstance(obj, functools.partial):
        obj = obj.func
    return inspect.iscoroutinefunction(obj)
