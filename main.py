from parser.ast import AST
from generator.generator import LLVMGenerator

if __name__ == '__main__':
    tree = AST("test/test.c")
    gen = LLVMGenerator()
    gen.visit(tree)
    gen.save("test.ll")
