import asyncio
import functools
import inspect

from inspect import isfunction, ismethod
from typing import (
    Union,
    Callable,
    Dict,
    Coroutine,
    Any,
    Awaitable,
    Iterable,
    Set
)


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

        ex_sync_tasks = self.__prepare_sync_checks()
        async_tasks = self.__prepare_async_checks()
        all_tasks = set((*ex_sync_tasks, *async_tasks))

        checks_results = await self.__run_check_tasks(all_tasks)

        self.__check_result_types(checks_results)

        if all(checks_results.values()) is True:
            code = self.__success_code
        else:
            code = self.__fail_code

        return HealthcheckResponse(checks_results, code)

    @staticmethod
    async def __check_wrapper(name: str, task: Awaitable):
        result = await task
        return name, result

    def __prepare_async_checks(self)->Iterable[Awaitable]:
        if len(self.async_checks) == 0:
            return set()

        prepared_tasks = {
            self.__check_wrapper(name, check())\
                for (name, check) in self.__async_healthchecks
        }

        return prepared_tasks

    def __prepare_sync_checks(self)->Iterable[Awaitable]:
        if len(self.sync_checks) == 0:
            return set()

        loop = asyncio.get_event_loop()
        prepared_tasks = set()

        for (name, check) in self.__sync_healthchecks:
            promise = loop.run_in_executor(None, check)
            check_task = self.__check_wrapper(name, promise)
            prepared_tasks.add(check_task)

        return prepared_tasks

    async def __run_check_tasks(
            self,
            checks_tasks: Iterable[Awaitable]
    )->CheckResult:
        done, pending = await asyncio.wait(
            checks_tasks,
            timeout=self.__timeout,
            return_when=asyncio.ALL_COMPLETED
        )

        result = {t.result()[0]: t.result()[1] for t in done}
        if len(pending) > 0:
            for t in pending:
                t.cancel()

            timed_out_checks = self.__get_unexisted_checks(result.keys())
            for check in timed_out_checks:
                result[check] = False

        return result

    def __get_unexisted_checks(self, check_names: Iterable[str])->Iterable[str]:
        all_checks = set((*self.sync_checks,*self.async_checks))

        res = set()
        for name in all_checks:
            if name not in check_names:
                res.add(name)
        return res

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

    async def aiohttp_handler(self, _):
        from aiohttp import web
        response = await self.check_handler()

        return web.json_response(response.body, status=response.code)


def iscoroutinefunction_or_partial(obj: Any):
    """
    This function check if object is coroutine
    or coroutine with partial wrapper.

    :param obj: Checked object
    :return: True if checked object is coroutine or coroutine
    with partial wrapper. False in all other cases.
    """
    if isinstance(obj, functools.partial):
        obj = obj.func
    return inspect.iscoroutinefunction(obj)
