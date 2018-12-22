from parser.CVisitor import CVisitor
from parser.CParser import CParser
import llvmlite.ir as ir
from generator.types import LLVMTypes
from generator.util import parse_escape


class LLVMGenerator(CVisitor):
    def __init__(self):
        self.module = ir.Module()
        self.local_vars = {}
        self.continue_block = None
        self.break_block = None

    @staticmethod
    def match_rule(ctx, rule):
        """判断ctx.getRuleIndex()==rule是否成立.若ctx无getRuleIndex()则返回False."""
        if hasattr(ctx, 'getRuleIndex'):
            return ctx.getRuleIndex() == rule
        else:
            return False

    @staticmethod
    def match_texts(ctx, texts):
        """判断ctx.getText() in texts是否成立.若ctx无getText()则返回False. texts是一个字符串列表"""
        if hasattr(ctx, 'getText'):
            return ctx.getText() in texts
        else:
            return False

    @classmethod
    def match_text(cls, ctx, text):
        """判断ctx.getText() == text是否成立.若ctx无getText()则返回False"""
        return cls.match_texts(ctx, [text])

    def visitFunctionDefinition(self, ctx:CParser.FunctionDefinitionContext):
        """
        functionDefinition
            :   declarationSpecifiers declarator compoundStatement
        eg: void hi(char *who, int *i);
        """
        ret_type = self.visit(ctx.declarationSpecifiers())  #函数返回值的类型
        ctx.declarator().base_type = ret_type
        func_name, function_type, arg_names = self.visit(ctx.declarator())
        llvm_function = ir.Function(self.module, function_type, name=func_name)
        self.builder = ir.IRBuilder(llvm_function.append_basic_block(name="entry"))

        self.local_vars[func_name] = llvm_function

        for arg_name, llvm_arg in zip(arg_names, llvm_function.args):
            self.local_vars[arg_name] = llvm_arg

        self.continue_block = None
        self.break_block = None

        self.visit(ctx.compoundStatement())

        # if function_type.return_type == LLVMTypes.void:
        #     self.builder.ret_void()

    def visitTypeSpecifier(self, ctx:CParser.TypeSpecifierContext):
        """
        typeSpecifier
            :   'void'
            |   'char'
            |   'short'
            |   'int'
            |   'long'
            |   'float'
            |   'double'
            |   typeSpecifier pointer
        :param ctx:
        :return: 对应的LLVM类型
        """
        if self.match_rule(ctx.children[0], CParser.RULE_typeSpecifier):
            # typeSpecifier pointer
            return LLVMTypes.get_pointer_type(self.visit(ctx.typeSpecifier()))
        elif self.match_texts(ctx, LLVMTypes.str2type.keys()):
            # void | char | short | int | long | float | double |
            return LLVMTypes.str2type[ctx.getText()]
        else:
            print("Error: unknown type ", ctx.getText())
            exit(-1)

    def visitParameterList(self, ctx:CParser.ParameterListContext):
        """
        parameterList
            :   parameterDeclaration
            |   parameterList ',' parameterDeclaration
            ;
        :param ctx:
        :return: 返回变量名字列表arg_names和变量类型列表arg_types
        """
        if len(ctx.children) == 1:
            arg_names = []
            arg_types = []
        else:
            arg_names, arg_types = self.visit(ctx.parameterList())
        arg_name, arg_type = self.visit(ctx.parameterDeclaration())
        arg_names.append(arg_name)
        arg_types.append(arg_type)
        return arg_names, arg_types

    def visitParameterDeclaration(self, ctx:CParser.ParameterDeclarationContext):
        """
        parameterDeclaration
            :   declarationSpecifiers declarator
            ;
        :param ctx:
        :return: 声明变量的名字和类型
        """
        base_type = self.visit(ctx.declarationSpecifiers())
        ctx.declarator().base_type = base_type  # 将声明变量的基础类型向下传递到declarator子树中
        arg_name, arg_type = self.visit(ctx.declarator())
        return arg_name, arg_type

    def visitDeclarator(self, ctx:CParser.DeclaratorContext):
        """
        declarator
            :   directDeclarator
            ;
        :param ctx:
        :return:
        """
        return self.visit(ctx.directDeclarator())

    def visitDirectDeclarator(self, ctx:CParser.DirectDeclaratorContext):
        """
        directDeclarator
            :   Identifier
            |   directDeclarator '[' assignmentExpression? ']'
            |   directDeclarator '(' parameterTypeList ')'
            |   directDeclarator '(' identifierList? ')'
            |   '(' typeSpecifier? pointer directDeclarator ')' // function pointer like: (__cdecl *f)
            ;
        :param ctx:
        :return: 声明变量的名字name,类型type,（如果是变量是函数，则还会返回所有参数的名字arg_names)
        """
        ctx.base_type = ctx.parentCtx.base_type  # 声明的基础数据类型
        if len(ctx.children) == 1:  # Identifier
            return ctx.getText(), ctx.base_type
        elif self.match_rule(ctx.children[0], CParser.RULE_directDeclarator):
            name, old_type = self.visit(ctx.directDeclarator())
            if ctx.children[1].getText() == '[':
                if self.match_text(ctx.children[2], ']'):  # directDeclarator '[' ']'
                    new_type = LLVMTypes.get_pointer_type(old_type)
                elif self.match_rule(ctx.children[2], CParser.RULE_assignmentExpression):
                    # directDeclarator '[' assignmentExpression ']'
                    array_size = int(ctx.children[2].getText())
                    new_type = LLVMTypes.get_array_type(elem_type=old_type, count=array_size)
                else:
                    print("Error :visitDirectDeclarator not finished yet.")
                    exit(-1)
                return name, new_type
            elif ctx.children[1].getText() == '(':
                name, old_type = self.visit(ctx.directDeclarator())
                if self.match_rule(ctx.children[2], CParser.RULE_parameterTypeList):
                    # directDeclarator '(' parameterTypeList ')'
                    arg_names, arg_types = self.visit(ctx.parameterTypeList())
                    new_type = ir.FunctionType(old_type, arg_types)
                    return name, new_type, arg_names
                elif self.match_rule(ctx.children[2], CParser.RULE_identifierList):
                    # directDeclarator '(' identifierList ')'
                    pass
                else:
                    # directDeclarator '(' ')'
                    arg_names = []
                    arg_types = []
                    new_type = ir.FunctionType(old_type, arg_types)
                    return name, new_type, arg_names
        # TODO '(' typeSpecifier? pointer directDeclarator ')'
        print("Error :visitDirectDeclarator not finished yet.")
        exit(-1)

    def visitAssignmentExpression(self, ctx:CParser.AssignmentExpressionContext):
        """
        assignmentExpression
            :   conditionalExpression
            |   unaryExpression assignmentOperator assignmentExpression
        :param ctx:
        :return: 表达式的值
        """
        if self.match_rule(ctx.children[0], CParser.RULE_conditionalExpression):
            return self.visit(ctx.conditionalExpression())
        elif self.match_rule(ctx.children[0], CParser.RULE_unaryExpression):
            lhs = self.visit(ctx.unaryExpression())
            op = self.visit(ctx.assignmentOperator())
            rhs = self.visit(ctx.assignmentExpression())
            # 根据不同的op进行运算
            if op == '=':
                converted_rhs = LLVMTypes.cast_type(self.builder, value=rhs, target_type=lhs.type.pointee)
                self.builder.store(converted_rhs, lhs)
                return converted_rhs
            else:
                # TODO 进行其他运算处理
                print("Error: visitAssignmentExpression not finished yet")
                exit(-1)

    def visitConditionalExpression(self, ctx:CParser.ConditionalExpressionContext):
        """
        conditionalExpression
            :   logicalOrExpression ('?' expression ':' conditionalExpression)?
        :param ctx:
        :return:表达式的值
        """
        # TODO
        return self.visit(ctx.logicalOrExpression())

    def visitLogicalOrExpression(self, ctx:CParser.LogicalOrExpressionContext):
        """
        logicalOrExpression
            :   logicalAndExpression
            |   logicalOrExpression '||' logicalAndExpression
            ;
        :param ctx:
        :return:表达式的值
        """
        rhs = self.visit(ctx.logicalAndExpression())
        if len(ctx.children) == 3:  # logicalOrExpression '||' logicalAndExpression
            lhs = self.visit(ctx.logicalOrExpression())
            converted_lhs = LLVMTypes.cast_type(self.builder, value=lhs, target_type=LLVMTypes.bool)
            converted_rhs = LLVMTypes.cast_type(self.builder, value=rhs, target_type=LLVMTypes.bool)
            return self.builder.or_(converted_lhs, converted_rhs)
        else:  # logicalAndExpression
            return rhs

    def visitUnaryExpression(self, ctx:CParser.UnaryExpressionContext):
        """
        unaryExpression
            :   postfixExpression
            |   '++' unaryExpression
            |   '--' unaryExpression
            |   unaryOperator castExpression
            |   'sizeof' unaryExpression
            |   'sizeof' '(' typeName ')'
            ;
        :param ctx:
        :return: 表达式的值，变量本身
        """
        if self.match_rule(ctx.children[0], CParser.RULE_postfixExpression):  # postfixExpression
            return self.visit(ctx.postfixExpression())
        elif self.match_texts(ctx.children[0], ['++', '--']):  # '++' unaryExpression | '--' unaryExpression
            lhs, lhs_ptr = self.visit(ctx.unaryExpression())
            one = ir.Constant(lhs_ptr.type, 1)
            if self.match_text(ctx.children[0], '++'):
                res = self.builder.add(lhs, one)
            else:
                res = self.builder.sub(lhs, one)
            self.builder.store(res, lhs_ptr)
            return res, lhs_ptr
        else:
            print("Error: visitUnaryExpression not finished yet.")
            exit(-1)


    def visitCastExpression(self, ctx:CParser.CastExpressionContext):
        """
        castExpression
            :   '(' typeName ')' castExpression
            |   unaryExpression
            ;
        :param ctx:
        :return: 表达式的值，变量本身
        """
        # TODO
        return self.visit(ctx.unaryExpression())

    def visitUnaryOperator(self, ctx:CParser.UnaryOperatorContext):
        """
        unaryOperator
            :   '&' | '*' | '+' | '-' | '~' | '!'
            ;
        :param ctx:
        :return:
        """
        return ctx.getText()

    def visitPostfixExpression(self, ctx:CParser.PostfixExpressionContext):
        """
        postfixExpression
            :   primaryExpression
            |   postfixExpression '[' expression ']'
            |   postfixExpression '(' argumentExpressionList? ')'
            |   postfixExpression '.' Identifier
            |   postfixExpression '->' Identifier
            |   postfixExpression '++'
            |   postfixExpression '--'
            ;
        :param ctx:
        :return: 表达式的值，变量本身
        """
        if self.match_rule(ctx.children[0], CParser.RULE_primaryExpression):  # primaryExpression
            return self.visit(ctx.primaryExpression())
        elif self.match_rule(ctx.children[0], CParser.RULE_postfixExpression):
            lhs, lhs_ptr = self.visit(ctx.postfixExpression())
            op = ctx.children[1].getText()
            if op == '[':  # postfixExpression '[' expression ']'
                array_index = self.visit(ctx.expression())
                ptr = self.builder.gep(lhs, [array_index])
                return self.builder.load(ptr), ptr
            elif op == '(':  # postfixExpression '(' argumentExpressionList? ')'
                if len(ctx.children) == 4:
                    args = self.visit(ctx.argumentExpressionList())
                else:
                    args = []
                converted_args = [LLVMTypes.cast_type(self.builder, value=arg, target_type=callee_arg.type)
                                  for arg, callee_arg in zip(args, lhs.args)]
                return self.builder.call(lhs, converted_args), None
        print("Error: visitPostfixExpression not finished yet.")
        exit(-1)

    def visitPrimaryExpression(self, ctx:CParser.PrimaryExpressionContext):
        """
        primaryExpression
            :   Identifier
            |   Constant
            |   StringLiteral+
            |   '(' expression ')'
        :param ctx:
        :return: 表达式的值，变量本身
        """
        if len(ctx.children) == 3:
            return self.visit(ctx.expression())
        else:
            text = ctx.getText()
            if ctx.Identifier():
                if text in self.local_vars:
                    var = self.local_vars[text]
                    if type(var) in [ir.Argument, ir.Function]:
                        var_val = var
                    else:
                        if isinstance(var.type.pointee, ir.ArrayType):
                            zero = ir.Constant(LLVMTypes.int, 0)
                            var_val = self.builder.gep(var, [zero, zero])
                        else:
                            var_val = self.builder.load(var)
                    return var_val, var
                else:
                    # TODO raise exception
                    print(self.module.functions)
                    print("Undefined identifier: '%s'\n" % text)
            elif ctx.StringLiteral():
                str_len = len(parse_escape(text[1:-1]))
                return LLVMTypes.get_const_from_str(LLVMTypes.get_array_type(LLVMTypes.char, str_len+1), text)
            else:
                # TODO 目前只接受整数
                return LLVMTypes.get_const_from_str(LLVMTypes.int, text)

    def visitArgumentExpressionList(self, ctx:CParser.ArgumentExpressionListContext):
        """
        argumentExpressionList
            :   assignmentExpression
            |   argumentExpressionList ',' assignmentExpression
            ;
        :param ctx:
        :return: 返回参数值的一个列表
        """
        if len(ctx.children) == 1:
            arg_list = []
        else:
            arg_list = self.visit(ctx.argumentExpressionList())
        arg = self.visit(ctx.assignmentExpression())
        arg_list.append(arg)
        return arg_list

    def visitJumpStatement(self, ctx:CParser.JumpStatementContext):
        """
        jumpStatement
            |   'continue' ';'
            |   'break' ';'
            |   'return' expression? ';'
            ;
        :param ctx:
        :return:
        """
        jump_str = ctx.children[0].getText()
        if jump_str == "return":
            if len(ctx.children) == 3:
                ret_val = self.visit(ctx.expression())
                converted_val = LLVMTypes.cast_type(
                    self.builder, target_type=self.builder.function.type.pointee.return_type, value=ret_val)
                self.builder.ret(converted_val)
            else:
                self.builder.ret_void()
        elif jump_str == 'continue':
            self.builder.branch(self.continue_block)
        elif jump_str == 'break':
            self.builder.branch(self.break_block)
        else:
            print("visitJumpStatement not finished yet.")
            exit(-1)

    def save(self, filename):
        """保存到文件"""
        with open(filename, "w") as f:
            f.write(repr(self.module))






