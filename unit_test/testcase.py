_cases = [
    "function.c",  #函数测试
    "initialize.c",  #变量初始化测试
    "pointer.c",  #指针测试
    "assignment_operator.c", # 赋值和运算符测试
    "loop.c",  # 循环测试
    "select.c",  # 选择分支测试
    "scope.c",  # 作用域测试
    "struct.c",  # 结构体和指针相关测试
    "array.c", #数组测试
    "unaryop.c", #一元运算符测试
]

def cases():
    return ["unit_test/"+case for case in _cases]
