from generator.generator import LLVMGenerator
from antlr4 import *
from parser.CLexer import CLexer
from parser.CParser import CParser
from generator.errors import *
import sys

if __name__ == '__main__':
    input_filename = "test/wrong.c"
    output_filename = "wrong.ll"
    if len(sys.argv) == 3:
        input_filename = sys.argv[1]
        output_filename = sys.argv[2]

    lexer = CLexer(FileStream(input_filename))
    stream = CommonTokenStream(lexer)
    parser = CParser(stream)

    error_listener = TinyCErrorListener()
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)

    tree = parser.compilationUnit()

    # if len(error_listener.errors) == 0:
    #     gen = LLVMGenerator(error_listener)
    #     gen.visit(tree)
    #     gen.save(output_filename)

    gen = LLVMGenerator(error_listener)
    gen.visit(tree)
    gen.save(output_filename)

    if len(error_listener.errors) == 0:
        print("success")
    else:
        error_listener.print_errors()
