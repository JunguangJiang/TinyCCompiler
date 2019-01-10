# 所有测试文件的名字
_cases = [
    "palindrome_en.c",
    "arithmetic_en.c",
    "KMP.c"
]


def cases():
    return ["test/"+case for case in _cases]
