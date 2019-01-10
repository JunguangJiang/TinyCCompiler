_cases = [
    "function.c",
    "initialize.c",
    "pointer.c",
    "task_3_to_7.c",
    "loop.c",
    "select.c",
]


def cases():
    return ["unit_test/"+case for case in _cases]
