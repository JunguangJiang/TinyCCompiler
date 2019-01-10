_cases = [
    "linkedlist2.c"
]

'''"
    "function.c",  #函数测试
    "initialize.c",  #变量初始化测试
    "pointer.c",  #指针测试
    "task_3_to_7.c",
    "loop.c",  # 循环测试
    "select.c",  # 选择分支测试
    "scope.c",  # 作用域测试'''

def cases():
    return ["unit_test/"+case for case in _cases]
