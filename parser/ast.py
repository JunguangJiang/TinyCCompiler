"""
将代码文件转化为抽象语法树
"""

from antlr4 import *
from parser.CLexer import CLexer
from parser.CParser import CParser


def AST(file_name):
    """
    :param file_name: 代码文件名
    :return: 生成的抽象语法树
    """
    lexer = CLexer(FileStream(file_name))
    stream = CommonTokenStream(lexer)
    parser = CParser(stream)
    tree = parser.compilationUnit()
    return tree
