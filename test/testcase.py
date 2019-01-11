# 所有测试文件的名字
_cases = [
    "palindrome.c",
    "arithmetic.c",
    "KMP.c",
    "linkedlist.c"
]


def cases():
    return ["test/"+case for case in _cases]
