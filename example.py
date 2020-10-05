import taskgraph

@taskgraph.delayed
def computation():
    return sum(range(100000000))

@taskgraph.delayed
def test():
    for _ in range(10):
        yield computation()

result = taskgraph.run(test(), max_workers=4)
print(result)
