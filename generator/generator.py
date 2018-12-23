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
        self.emit_printf()
        self.current_base_type = None  #当前上下文的基础数据类型
        self.is_global = True  #当前是否处于全局环境中

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

    def emit_printf(self):
        """引入printf函数"""
        printf_type = ir.FunctionType(LLVMTypes.int, (LLVMTypes.get_pointer_type(LLVMTypes.char),), var_arg=True)
        printf_func = ir.Function(self.module, printf_type, "printf")
        self.local_vars["printf"] = printf_func

    def visitDeclaration(self, ctx:CParser.DeclarationContext):
        """
        declaration
            :   declarationSpecifiers initDeclaratorList ';'
            | 	declarationSpecifiers ';'
            ;
        :param ctx:
        :return:
        """
        var_type = self.visit(ctx.declarationSpecifiers())  #类型
        self.current_base_type = var_type
        if len(ctx.children) == 3:
            self.visit(ctx.initDeclaratorList())

    def visitFunctionDefinition(self, ctx:CParser.FunctionDefinitionContext):
        """
        functionDefinition
            :   declarationSpecifiers declarator compoundStatement
        eg: void hi(char *who, int *i);
        """
        self.is_global = False
        ret_type = self.visit(ctx.declarationSpecifiers())  #函数返回值的类型
        self.current_base_type = ret_type
        # ctx.declarator().base_type = ret_type  # 将函数返回值类型ret_type向下传递到declarator子树中
        func_name, function_type, arg_names = self.visit(ctx.declarator())  # 获得函数名、函数类型、参数名列表
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
        self.is_global = True

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
        # base_type = self.visit(ctx.declarationSpecifiers())
        self.current_base_type = self.visit(ctx.declarationSpecifiers())
        # ctx.declarator().base_type = base_type  # 将声明变量的基础类型向下传递到declarator子树中
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
        # ctx.base_type = ctx.parentCtx.base_type  # 声明的基础数据类型,自上而下传递
        if len(ctx.children) == 1:  # Identifier
            return ctx.getText(), self.current_base_type
        elif self.match_rule(ctx.children[0], CParser.RULE_directDeclarator):
            name, old_type = self.visit(ctx.directDeclarator())
            if ctx.children[1].getText() == '[':
                if self.match_text(ctx.children[2], ']'):  # directDeclarator '[' ']'
                    new_type = LLVMTypes.get_pointer_type(old_type)
                else:  # directDeclarator '[' assignmentExpression ']'
                    array_size = int(ctx.children[2].getText())
                    new_type = LLVMTypes.get_array_type(elem_type=old_type, count=array_size)
                return name, new_type
            elif ctx.children[1].getText() == '(':
                if self.match_rule(ctx.children[2], CParser.RULE_parameterTypeList):
                    # directDeclarator '(' parameterTypeList ')'
                    arg_names, arg_types = self.visit(ctx.parameterTypeList())  # 获得函数参数的名字列表和类型列表
                    new_type = ir.FunctionType(old_type, arg_types)
                    return name, new_type, arg_names
                elif self.match_rule(ctx.children[2], CParser.RULE_identifierList):
                    # TODO directDeclarator '(' identifierList ')'
                    pass
                else:
                    # directDeclarator '(' ')'
                    arg_names = []
                    arg_types = []
                    new_type = ir.FunctionType(old_type, arg_types)
                    return name, new_type, arg_names
        else:
            # TODO '(' typeSpecifier? pointer directDeclarator ')'
            pass
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
            lhs, lhs_ptr = self.visit(ctx.unaryExpression())
            op = self.visit(ctx.assignmentOperator())
            rhs = self.visit(ctx.assignmentExpression())
            # TODO 根据不同的op进行运算
            if op == '=':
                # 此处存疑 ？
                converted_rhs = LLVMTypes.cast_type(self.builder, value=rhs, target_type=lhs_ptr.type.pointee)
                self.builder.store(converted_rhs, lhs_ptr)
                return converted_rhs
            else:
                print("Error: visitAssignmentExpression not finished yet")
                exit(-1)

    def visitAssignmentOperator(self, ctx:CParser.AssignmentOperatorContext):
        """
        assignmentOperator
            :   '=' | '*=' | '/=' | '%=' | '+=' | '-=' | '<<=' | '>>=' | '&=' | '^=' | '|='
            ;
        :param ctx:
        :return:
        """
        return ctx.getText()

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
        if len(ctx.children) == 1:  # logicalAndExpression
            return rhs
        else:  # logicalOrExpression '||' logicalAndExpression
            lhs = self.visit(ctx.logicalOrExpression())
            converted_lhs = LLVMTypes.cast_type(self.builder, value=lhs, target_type=LLVMTypes.bool)
            converted_rhs = LLVMTypes.cast_type(self.builder, value=rhs, target_type=LLVMTypes.bool)
            return self.builder.or_(converted_lhs, converted_rhs)

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
            one = LLVMTypes.int(1)
            if self.match_text(ctx.children[0], '++'):
                res = self.builder.add(lhs, one)
            else:
                res = self.builder.sub(lhs, one)
            self.builder.store(res, lhs_ptr)
            return res, lhs_ptr
        else:
            # TODO
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
        :return: 一元运算符对应的符号
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
                if len(converted_args) < len(args):  # 考虑变长参数
                    converted_args += args[len(lhs.args):]
                return self.builder.call(lhs, converted_args), None
        else:
            # TODO
            pass
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
            return self.visit(ctx.expression()), None
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
                return LLVMTypes.get_const_from_str(LLVMTypes.get_array_type(LLVMTypes.char, str_len+1), text), None
            else:
                # TODO 目前只接受整数
                const_value = LLVMTypes.get_const_from_str(LLVMTypes.int, text)
                return const_value, None

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
            # TODO 尚未支持goto语句
            print("visitJumpStatement not finished yet.")
            exit(-1)

    def visitMultiplicativeExpression(self, ctx:CParser.MultiplicativeExpressionContext):
        """
        multiplicativeExpression
            :   castExpression
            |   multiplicativeExpression '*' castExpression
            |   multiplicativeExpression '/' castExpression
            |   multiplicativeExpression '%' castExpression
            ;
        :param ctx:
        :return: 表达式的值
        """
        rhs, rhs_ptr = self.visit(ctx.castExpression())
        if self.match_rule(ctx.children[0], CParser.RULE_castExpression):
            return rhs
        else:
            lhs, lhs_ptr = self.visit(ctx.multiplicativeExpression())
            converted_target = lhs.type
            converted_rhs = LLVMTypes.cast_type(self.builder, value=rhs, target_type=converted_target)  # 将rhs转成lhs的类型
            op = ctx.children[1].getText()
            if LLVMTypes.is_int(converted_target): # 整数运算
                if op == '*':
                    return self.builder.mul(lhs, converted_rhs)
                elif op == '/':
                    return self.builder.sdiv(lhs, converted_rhs)
                else:
                    return self.builder.srem(lhs, converted_rhs)
            elif LLVMTypes.is_float(converted_target):  #浮点数运算
                if op == '*':
                    return self.builder.fmul(lhs, converted_rhs)
                elif op == '/':
                    return self.builder.fdiv(lhs, converted_rhs)
                else:
                    # TODO raise exception
                    print("浮点数不支持%运算!")
                    exit(-1)
            else:
                # TODO raise exception
                print("Error: 未知的运算", lhs, op, rhs)

    def visitInitDeclarator(self, ctx:CParser.InitDeclaratorContext):
        """
        initDeclarator
            :   declarator
            |   declarator '=' initializer
            ;
        :param ctx:
        :return:
        """
        var_name, var_type = self.visit(ctx.declarator())
        if len(ctx.children) == 3:
            init_val = self.visit(ctx.initializer())
            # TODO 针对initializer的各种情况进行讨论: 可能是一个值，也可能是一个列表
            if isinstance(var_type, ir.PointerType) and isinstance(init_val.type, ir.ArrayType) and var_type.pointee == init_val.type.element:
                var_type = init_val.type  #这个处理有必要吗？
            converted_val = LLVMTypes.cast_type(self.builder, value=init_val, target_type=var_type)

        if self.is_global:
            self.local_vars[var_name] = ir.GlobalVariable(self.module, var_type, name=var_name)
            self.local_vars[var_name].linkage = "internal"
            if len(ctx.children == 3):
                self.local_vars[var_name].initializer = converted_val
        else:
            self.local_vars[var_name] = self.builder.alloca(var_type)
            if len(ctx.children) == 3:
                self.builder.store(converted_val, self.local_vars[var_name])

    def visitIterationStatement(self, ctx:CParser.IterationStatementContext):
        """
        iterationStatement
            :   While '(' expression ')' statement
            |   Do statement While '(' expression ')' ';'
            |   For '(' forCondition ')' statement
            ;
        :param ctx:
        :return:
        """
        name_prefix = self.builder.block.name
        cond_block = self.builder.append_basic_block(name=name_prefix+".loop_cond")  # 条件判断语句块，例如i<3
        loop_block = self.builder.append_basic_block(name=name_prefix+".loop_body")  # 循环语句块
        end_block = self.builder.append_basic_block(name=name_prefix+".loop_end")  # 循环结束后的语句块
        update_block = self.builder.append_basic_block(name_prefix+".loop_update")  # 值更新语句块，例如i++

        # 保存原先的continue_block和break_block
        last_continue, last_break = self.continue_block, self.break_block
        self.continue_block, self.break_block = update_block, end_block

        iteration_type = ctx.children[0].getText()  # 循环类型

        cond_expression = None
        update_expression = None
        if iteration_type == "while":  # while循环
            cond_expression = ctx.expression()
        elif iteration_type == "for":  # for循环
            cond_expression, update_expression = self.visit(ctx.forCondition())
        else:  # do-while循环
            print("do while not finished yet.")
            exit(-1)

        self.builder.branch(cond_block)
        self.builder.position_at_start(cond_block)
        if cond_expression:
            cond_val = self.visit(cond_expression)
            converted_cond_val = LLVMTypes.cast_type(self.builder, target_type=LLVMTypes.bool, value=cond_val)
            self.builder.cbranch(converted_cond_val, loop_block, end_block)
        else:
            self.builder.branch(loop_block)

        self.builder.position_at_start(loop_block)
        self.visit(ctx.statement())
        self.builder.branch(update_block)

        self.builder.position_at_start(update_block)
        if update_expression:
            self.visit(update_expression)
        self.builder.branch(cond_block)

        # 恢复原先的continue_block和break_block
        self.builder.position_at_start(end_block)
        self.continue_block = last_continue
        self.break_block = last_break

    def visitForCondition(self, ctx:CParser.ForConditionContext):
        """
        forCondition
            :   forDeclaration ';' forExpression? ';' forExpression?
            |   expression? ';' forExpression? ';' forExpression?
            ;
        :param ctx:
        :return: 循环判断表达式cond_expression,循环更新表达式update_expression,如果不存在则返回None
        """
        idx = 0
        if self.match_rule(ctx.children[idx], CParser.RULE_forDeclaration):
            idx += 2
            self.visit(ctx.forDeclaration())
        elif self.match_rule(ctx.children[idx], CParser.RULE_expression):
            idx += 2
            self.visit(ctx.expression())
        else:
            idx += 1

        cond_expression = None
        update_expression = None
        if self.match_rule(ctx.children[idx], CParser.RULE_forExpression):
            cond_expression = ctx.children[idx]
            idx += 2
        else:
            idx += 1

        if idx == len(ctx.children) - 1:
            update_expression = ctx.children[idx]

        return cond_expression, update_expression

    def visitForDeclaration(self, ctx:CParser.ForDeclarationContext):
        """
        forDeclaration
            :   declarationSpecifiers initDeclaratorList
            | 	declarationSpecifiers
            ;
        :param ctx:
        :return:
        """
        var_type = self.visit(ctx.declarationSpecifiers())  # 类型
        self.current_base_type = var_type
        if len(ctx.children) == 2:
            self.visit(ctx.initDeclaratorList())

    def visitSelectionStatement(self, ctx:CParser.SelectionStatementContext):
        """
        selectionStatement
            :   'if' '(' expression ')' statement ('else' statement)?
            |   'switch' '(' expression ')' statement
            ;
        :param ctx:
        :return:
        """
        if ctx.children[0].getText() == 'if':
            cond_val = self.visit(ctx.expression())
            converted_cond_val = LLVMTypes.cast_type(self.builder, target_type=LLVMTypes.bool, value=cond_val)
            statements = ctx.statement()
            if len(statements) == 2:  # 存在else分支
                with self.builder.if_else(converted_cond_val) as (then, otherwise):
                    with then:
                        self.visit(statements[0])
                    with otherwise:
                        self.visit(statements[1])
            else:  # 只有if分支
                with self.builder.if_then(converted_cond_val):
                    self.visit(statements[0])
        else:
            # TODO
            print("switch not finished yet.")
            exit(-1)

    def save(self, filename):
        """保存到文件"""
        with open(filename, "w") as f:
            f.write(repr(self.module))






