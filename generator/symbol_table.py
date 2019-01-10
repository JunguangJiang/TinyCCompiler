import unittest


class RedefinitionError(Exception):
    """重定义错误"""
    def __init__(self, name):
        """
        :param name: 重定义的变量名
        """
        self.name = name


class SymbolTable:
    """符号表"""
    def __init__(self):
        self.__tables = [{},]
        self.__level = 0  # 当前的嵌套层数

    def __getitem__(self, item):
        for l in range(self.__level, -1, -1):
            if item in self.__tables[l]:
                return self.__tables[l][item]
        return None

    def __setitem__(self, key, value):
        if key in self.__tables[self.__level]:
            raise RedefinitionError(key)
        self.__tables[self.__level][key] = value

    def __contains__(self, item):
        for l in range(self.__level, -1, -1):
            if item in self.__tables[l]:
                return True
        return False

    def enter_scope(self):
        """进入一个新的作用域"""
        self.__level += 1
        self.__tables.append({})

    def exit_scope(self):
        """退出一个作用域"""
        if self.__level == 0:
            return
        self.__tables.pop(-1)
        self.__level -= 1


class SymbolTableTest(unittest.TestCase):
    """符号表单元测试"""
    def setUp(self):
        self.symbol_table = SymbolTable()

    def tearDown(self):
        pass

    def test_1(self):
        """内层变量覆盖外层同名变量"""
        self.symbol_table["abc"] = 123
        self.symbol_table.enter_scope()
        self.assertEqual(self.symbol_table["abc"],123)
        self.symbol_table["abc"] = 333
        self.assertEqual(self.symbol_table["abc"], 333)
        self.symbol_table.exit_scope()
        self.assertEqual(self.symbol_table["abc"], 123)

    def test_2(self):
        """离开当前作用域后需要删除临时变量"""
        self.symbol_table.enter_scope()
        self.symbol_table["abc"] = 333
        self.assertEqual(self.symbol_table["abc"], 333)
        self.symbol_table.exit_scope()
        self.assertIsNone(self.symbol_table["abc"])


if __name__ == '__main__':
    unittest.main()