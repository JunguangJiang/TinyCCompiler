from generator.generator import generate
import sys

if __name__ == '__main__':
    input_filename = "test/wrong.c"
    output_filename = "wrong.ll"
    if len(sys.argv) == 3:
        input_filename = sys.argv[1]
        output_filename = sys.argv[2]

    generate(input_filename, output_filename)