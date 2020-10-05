# python-taskgraph
A simple python library that run a DAG of computations in parallel.

The two main features are
1. computations can generate new computations, meaning the DAG can evolve during its execution
2. dynamic scaling of workers

It provides telnet interface on port `8888` that allows one to change the maximum number of parallel workers used.

## Usage
The basis of this library is the `DC` (Delayed Computation) object. It is formed by a function `func` that does the actual computation and (keyword) arguments given to the function:
```python
computation = DC(func, *args, **kwargs)
```
The (keyword) arguments itself can be `DC` objects aswell as normal values. If they are `DC` objects,
they get executed before calling the function `func` with their result. 
The return value of `func` can also be a `DC` object or a normal value. If it is a `DC`, it gets executed aswell, before finally returning the result. 

To run a `DC` one simply calls the `run` function, providing a initial value for the maximum parallel workers:
```python
import taskgraph
computation = taskgraph.DC(func, *args, **kwargs)
result = run(computation, max_workers = ...)
```

Finally this library provides a decorator `@delayed` that can be used to convert existing functions
into delayed computations. If the existing function is a generator, the values it `yield`s are
ran in parallel (if they are `DC`s) and returned as a list of the results:

```python
import taskgraph

@taskgraph.delayed
def computation():
    return sum(range(100000000))

@taskgraph.delayed
def test():
    for _ in range(3):
        yield computation()

result = taskgraph.run(test(), max_workers=4)
assert result == [4999999950000000, 4999999950000000, 4999999950000000]
```

This also provides a simple telnet API to allow dynamic scaling of the number of worker threads,
currently it accepts two commands:
1. `get_max_workers` returns the current maximum number of workers
2. `set_max_workers n` sets the maximum number of workers to `n`
