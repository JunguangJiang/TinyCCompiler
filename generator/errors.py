from antlr4.error.ErrorListener import ErrorListener


class SemanticError(Exception):
    """语义错误基类"""
    def __init__(self, msg, ctx=None):
        super().__init__()
        if ctx:
            self.line = ctx.start.line  #错误出现位置
            self.column = ctx.start.column
        else:
            self.line = 0
            self.column = 0
        self.msg = msg

    def __str__(self):
        return "SemanticError: " + str(self.line) + ":" + str(self.column) + " " + self.msg


class TinyCErrorListener(ErrorListener):
    """错误监听器"""
    def __init__(self):
        super().__init__()
        self.errors = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        """进行语法分析时，若出现语法错误自动调用该函数"""
        exception = "Syntax Error: " + str(line) + ":" + str(column) + " " + msg
        self.errors.append(exception)

    def register_semantic_error(self, error):
        """在进行语义分析时，在结束语义错误异常时，需手动调用该函数，error是错误异常类"""
        self.errors.append(str(error))

    def print_errors(self):
        """打印错误"""
        for err in self.errors:
            print(err)
        print(len(self.errors), "errors generated.")

