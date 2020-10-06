import functools
import asyncio
import inspect
from asyncio import Future
from threading import Thread
from process import Pool
from functools import partial
import dill
import cli

class Option:
    def __init__(self, *args):
        assert len(args) < 2

        if len(args) == 1:
            self.value = args[0]

    def is_none(self):
        return not hasattr(self, "value")

    def is_some(self):
        return hasattr(self, "value")

class DC:
    def __init__(self, func, *args, **kwargs):
       self._star_args = args
       self._starstar_args = kwargs
       self._func = func

       self._result = Option()
       self._future = None
       self._is_done = False
       setattr(self, "_DC_MAGIC_svtjnmb3jIpT2OWeKJWbJWoWuB+Rf/R7oOcr33RIlV8Z", None)

    # if the DC gets pickled and shipped away, a new object is created after it is unpickled and we can't track the completion, so silence the unused warning for DCs that get pickled
    def __getstate__(self):
        state = self.__dict__.copy()
        self._got_pickled = True
        return state

    def is_done(self):
        return self._result.is_some()

    def __del__(self):
        if (self._future is None or not self._future.done()) and not self._is_done and not hasattr(self, "_got_pickled"):
            print("WARNING: unused delayed computation", self, self._func, self._star_args, self._starstar_args)

def _make_list(*args):
    if len(args) > 1:
        return list(args)
    elif len(args) == 1:
        return args[0]
    else:
        return args

def _grab_everything_and_make_a_list(generator):
    items = list(generator)
    return DC(_make_list, *items)

def delayed(f):
    @functools.wraps(f)
    def g(*args, **kwargs):
        if inspect.isgeneratorfunction(f):
            def wrappping_function(*args, **kwargs):
                return list(f(*args, **kwargs))

            result = DC(wrappping_function, *args, **kwargs)
            return DC(_grab_everything_and_make_a_list, result)
        else:
            result = DC(f, *args, **kwargs)
            return result

    return g

def _is_dc(c):
    return hasattr(c, "_DC_MAGIC_svtjnmb3jIpT2OWeKJWbJWoWuB+Rf/R7oOcr33RIlV8Z")


def _dill_runner(func, args, kwargs):
    func = dill.loads(func)
    args = dill.loads(args)
    kwargs = dill.loads(kwargs)
    return dill.dumps(func(*args, **kwargs))

def submit_to_pool(loop, pool, func, *args, **kwargs) -> Future:
    future = Future()

    def set_result(result):
        loop.call_soon_threadsafe(future.set_result, dill.loads(result))

    def set_error(e):
        loop.call_soon_threadsafe(future.set_exception, e)

    pool.apply_async(_dill_runner, callback=set_result, error_callback=set_error, args=(dill.dumps(func), dill.dumps(args), dill.dumps(kwargs)))

    return future


async def run_async(delayed_computation):
    if not _is_dc(delayed_computation):
        # print(delayed_computation, "is not a delayed computation, returning immediately", delayed_computation)
        return delayed_computation

    # print("running", delayed_computation, delayed_computation._func, delayed_computation._star_args, delayed_computation._starstar_args)

    futures = []

    for arg in delayed_computation._star_args:
        if _is_dc(arg):
            if arg._future is None:
                arg._future = asyncio.create_task(run_async(arg))

            futures.append(arg._future)

    for arg in delayed_computation._starstar_args.values():
        if _is_dc(arg):
            if arg._future is None:
                arg._future = asyncio.create_task(run_async(arg))

            futures.append(arg._future)

    if len(futures) > 0:
        _ = await asyncio.wait(futures)

    star_args = []
    for arg in delayed_computation._star_args:
        if _is_dc(arg):
            star_args.append(arg._future.result())
        else:
            star_args.append(arg)

    starstar_args = {}
    for name, arg in delayed_computation._starstar_args:
        if _is_dc(arg):
            starstar_args[name] = arg._future.result()
        else:
            starstar_args[name] = arg

    result = await submit_to_pool(_taskgraph_loop, _taskgraph_p, partial(delayed_computation._func, *star_args, **starstar_args))
    delayed_computation._is_done = True

    result = await run_async(result)
    return result


def run(computation: DC, max_workers):
    global _taskgraph_loop
    global _taskgraph_p
    _taskgraph_loop = asyncio.get_event_loop()
    _taskgraph_p = Pool(max_workers)


    def set_max_workers(max_workers: int):
        global _taskgraph_p
        _taskgraph_p.resize(max_workers)
        return "{} {}".format("setting max workers to", max_workers)

    def get_max_workers():
        global _taskgraph_p
        return str(_taskgraph_p._processes)

    asyncio.run_coroutine_threadsafe(cli.cli_main(cli.cli_builder({set_max_workers, get_max_workers})), _taskgraph_loop)
    result = _taskgraph_loop.run_until_complete(run_async(computation))

    _taskgraph_p.close()
    _taskgraph_p.join()

    return result
