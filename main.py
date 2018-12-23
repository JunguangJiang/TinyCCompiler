from generator.generator import LLVMGenerator
from antlr4 import *
from parser.CLexer import CLexer
from parser.CParser import CParser
from generator.errors import *

if __name__ == '__main__':
    input_filename = "test/wrong.c"
    output_filename = "wrong.ll"

    lexer = CLexer(FileStream(input_filename))
    stream = CommonTokenStream(lexer)
    parser = CParser(stream)

    error_listener = TinyCErrorListener()
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)

    tree = parser.compilationUnit()

    if len(error_listener.errors) == 0:
        gen = LLVMGenerator(error_listener)
        gen.visit(tree)
        gen.save(output_filename)

    if len(error_listener.errors) == 0:
        print("success")
    else:
        error_listener.print_errors()
