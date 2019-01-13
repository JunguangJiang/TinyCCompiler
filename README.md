本文的石墨文档链接 [https://shimo.im/docs/CNQYjCjRt3QF89hz](https://shimo.im/docs/CNQYjCjRt3QF89hz)
github地址 [https://github.com/JunguangJiang/TinyCCompiler/tree/master](https://github.com/JunguangJiang/TinyCCompiler/tree/master)
# 开发环境
python 3.6
ANTLR 可通过pip install antlr4-python3-runtime安装
LLVM 可通过pip install llvmlite安装
# 代码结构
* parser
  * C.g4 C语言的完整语法文件，来自于[ANTLR官方对C语言的支持](https://github.com/antlr/grammars-v4/blob/master/c/C.g4)
  * CLexer.py 由C.g4自动生成的词法分析代码
  * CParser.py 由C.g4自动生成的语法分析代码
  * CVistor.py 我们的语义分析基于ANTLR的Visitor模式进行
* generator
  * generator.py 实现从C语言代码转成LLLVM IR代码
  * symbol_table.py 实现符号表
  * types.py 封装C语言中的基本类型，以及基本类型之间的转换
  * errors.py 实现语言异常类，以及对转换过程中的语法与语义错误进行监听
  * util.py 其他的常用函数
* executor
  * executor.py LLVM IR代码的解释器
* test
  * testcase.py 自动测试时所有需要执行的测试文件，具体如下
```
"arithmetic.c", # 四则运算测试
"palindrome.c"， # 回文测试
"KMP.c"，  # KMP测试文件
"AVLTree.c", # AVL树
"linkedlist.c", # 链表
"fibonacci.c"， # 斐波那契数计算，需要通过命令交互得到结果，因此不会进行自动测试
```
* unit_test 在开发过程中，为了保证团队的代码不互相干扰，针对C语言的各个功能特性，编写了一系列的功能测试脚本，每个脚本以.c结尾，程序正确运行时的输出在.txt文件中。
  * testcase.py 所有的测试文件名字，以及负责测试的功能，具体如下
```
"function.c",  # 函数测试
"initialize.c",  # 变量初始化测试
"pointer.c",  #指针测试
"assignment_operator.c", # 赋值和运算符测试
"loop.c",  # 循环测试
"select.c",  # 选择分支测试
"scope.c",  # 作用域测试
"struct.c",  # 结构体和指针相关测试
"array.c", # 数组测试
"unaryop.c", # 一元运算符测试
```
* test.py 运行自动测试
* main.py 编译C语言生成IR代码（但不运行）
# 使用说明
0. 下述所有命令都必须在main.py同级目录下执行。

1. 编译代码
```
python main.py 输入的C文件
```
例如
```
python main.py test/arithmetic.c
```

注：如果想要合并编译和执行的步骤可以参考“3.测试”，运行以下命令
```
python test.py test/arithmetic.c
```

2. 执行IR代码
```
python executor/executor.py test/arithmetic.ll
```

3. 测试

运行test/testcase.py下的所有测试(不打印异常）
```
python test.py
```

运行unit_test/testcase.py下的所有测试(不打印异常，需要在unit_test下提供相应的输出文件.txt,测试脚本会自动判断程序的输出是否正确）
```
python test.py unit
```

对某个特定的C语言文件hello.c进行测试（打印异常）
```
python test.py test/arithmetic.c
```
# 功能实现与难点
## 符号表
为每个作用域维护一层符号表，根据变量名或者函数名进行查找时，首先从最深层的符号表进行查找。局部作用域包括函数体内部、循环内部以及选择分支内部。
当离开一个作用域时，会将该层对应的符号表删除。
具体实现见generator/symbol_table.py。
作用域相关的测试代码见unit_test/scope.c。
## 错误处理
包括两类错误，
语法错误SyntaxError，由CParser在进行语法分析时产生，TinyCErrorListener (generator/errors.py)会监听所有的SyntaxError。
语义错误SemanticError(generator/errors.py), 由generator/generator.py中进行语义分析时，调用raise SemanticError产生。而SemanticError的捕获是以语句块（blockItem或者externalDeclaration)为单位的。也就是说，编译器会在某行代码出现错误后跳过该行代码，继续编译下一行代码。在编译结束后，会打印出所有的语法和语义错误。
目前能够检测到的语义错误包括：
* 变量名重定义
* 变量名未定义
* 函数定义和声明的类型（包括参数类型）不匹配
* 数组声明的范围不合法（不是正整数）
* break和continue出现在非循环语句块中
* 不合法的运算符（比如浮点数取模等）
* 不支持的类型转换
## 运算符及优先级
* 支持所有的二元运算符，
  * 算术运算符（+, -, *, /, %）
  * 位运算符（&, |, ^, >>, <<）
  * 逻辑运算符（&&, ||(实现短路原则), !, ~）
  * 关系运算符（<, >, <=, >=, !=, ==）。
* 支持三元运算符，即条件表达式“...?...:...”，采用分支和临时变量实现，即判断条件后执行对应的表达式求值，存放在临时变量中作为条件表达式的返回值。
* 支持所有的赋值运算符，包括=, *=, /=, %=, +=, -=, <<=, >>=, &=, ^=, |=。
* 优先级从低到高为：赋值运算符 < 三元运算符 < “||” < “&&” < “|” < “^” <  “&” < “==, !=” < “<, >, <=, >=” < “<<, >>” < “+, -” < “*, /, %”。
* 支持前加减、后加减
## 基本变量类型及其转换
* 支持的变量类型包括int,short,char,bool,float,double和void。
* 支持整数的扩展和截取、浮点数精度的调整、整数到布尔值的转换、整数和浮点数的相互转换、整数和指针的相互转换、不同指针类型的转换（由generator/types.py的cast_type实现）。
* 在变量赋值时，如果变量类型与值不匹配，则会对值进行强制转换。
* char的支持'3', '\n', '\0', 0等形式的赋值（由generator/types.py的get_const_from_str实现）。

注：为了能够调用malloc和free函数，需要实现unsigned类型，此处采用比较简单的策略——忽视所有的unsigned，当代码中出现unsigned int时，对应的依然是int类型。
## 选择结构程序设计
* 支持if, if-else, switch-case语句。
* 其中，switch-case语句支持default语句和break跳转，以及没有break时case语句从上而下依次执行，实现时将标签和语句块分开，一旦标签匹配上则从对应位置向下开始执行语句，直到break（或return）或语句块结束。
## 循环结构程序设计
* 支持for、do-while、while三种循环。
* 支持break和continue跳转。当进入一个新的循环块时，会同时维护旧的break、continue块和新的break、continue块，从而保证多层循环能够正确的跳转。
* for循环与标准的C for循环基本一致，初始化条件可以是多条语句（以','分割）
## 数组
支持多维数组，初始化时采用嵌套的方式进行初始化（如下所示）。
```
int array[3][4] = {
    {1,2,3,4},
    {5,6,7,8},
    {9,11,12,13}
};
```
可以通过char []定义任意长度的字符串
```
char c[] = "Hello world";
```
## 函数
* 实现了函数的声明和定义。
* 支持变长参数。通过识别'...'来判断函数是否变长。
* 支持函数的递归调用。见测试test/fibonacci.c.
* 通过声明库函数的方式可以调用库函数，例如printf,scanf,exit等。
* 相关的测试代码见unit_test/function.c。
## 指针
* 支持指针的定义。
* 支持取地址运算符&。
* 可以通过指针运算符*访问指针指向的对象。
* 支持指针的嵌套，即int **p。
* 支持字符串定义，如下所示。
```
char *c = "Hello world";
```
## 结构体
* 支持结构体的声明和定义。
* 支持.和->运算符用于获取结构体的成员。
* 结构体内支持其他结构体类型、基本数据类型（包括指针类型）作为成员变量。
* 结构体内支持指向自身结构体类型的指针，可实现链表及各种高级数据结构的定义。

测试见linkedlist.c和AVLTree.c，分别实现了基础的链表和AVL树。
在AVLTree.c中，实现了一颗简易版平衡二叉树，能够插入结点和打印树的结构，但是由于时间原因（以及数据结构课没学好）现在不能删除已经插入的结点。该文件的实现用到了c语言中大量语法特性，可以相对比较充分地展示我们的TinyCCompiler的功能。包括库函数（malloc、free、printf）调用，函数定义，结构体声明，结构体定义，结构体指针，指向结构体指针的指针，多层函数的递归调用，switch-case、if-else控制流语句等等。

