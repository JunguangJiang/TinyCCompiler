from generator.generator import generate
from executor.executor import execute
import sys
import test.testcase
import unit_test.testcase
import os
import filecmp
import traceback

def test_file(filename, print_exception=True):
    """
    测试filename代码的编译与执行
    :param filename:
    :param print_exception: 是否打印异常
    :return: 是否正确编译与执行
    """
    output_filename = filename.split('.')[0]+".ll"

    if print_exception:
        generate_result = generate(input_filename=filename, output_filename=output_filename)
    else:
        try:
            generate_result = generate(input_filename=filename, output_filename=output_filename)
        except Exception:
            print("generate", filename, "failed.")
            return False

    if not generate_result:
        print("generate", filename, "failed.")
        return False
    else:
        if print_exception:
            execute_result = execute(output_filename)
        else:
            try:
                execute_result = execute(output_filename)
            except Exception as e:
                print("execute", output_filename, "failed.")
                traceback.print_exc()
                return False

        return True


def test_files(filenames, print_exception=False, is_unit=False):
    """
    测试文件列表filenames中的所有文件
    :param filenames:
    :param print_exception: 是否打印异常
    :param is_unit: 是否是单元测试
    :return: None
    """
    success_numbers = 0
    fail_numbers = 0
    for filename in filenames:
        print("Test:",filename)
        if is_unit:
            result = unit_test_file(filename)
        else:
            result = test_file(filename, print_exception)

        if result:
            success_numbers += 1
        else:
            fail_numbers += 1
        print()
    print("Test Results:", success_numbers, "success,", fail_numbers, "fails")


def unit_test_file(filename):
    """
    单元测试filename代码的编译与执行
    :param filename:
    :return: 是否正确编译与执行
    """
    #todo htx 改回来
    os.system("python test.py " + filename + " > " + "unit_test/temp.txt")
    if filecmp.cmp(filename.split('.')[0]+".txt", "unit_test/temp.txt"):
        return True
    else:
        with open("unit_test/temp.txt") as f:
            print(f.read())
        print("Fail to pass", filename)
        return False


if __name__ == '__main__':
    #todo htx改回来
    #if len(sys.argv) == 2:
    if len(sys.argv) == 2:
        test_file(filename=sys.argv[1], print_exception=True)
    else:
        test_files(filenames=unit_test.testcase.cases(), print_exception=False)
    '''
    if True:
        # if sys.argv[1] == "unit":  # 运行单元测试文件
        if True:
            test_files(filenames=unit_test.testcase.cases(), print_exception=False, is_unit=True)
        else:  # 运行某个特定的C文件进行测试
            test_file(filename=sys.argv[1], print_exception=True)
    else:  # 运行测试文件
        test_files(filenames=test.testcase.cases(), print_exception=False, is_unit=False)
        '''


