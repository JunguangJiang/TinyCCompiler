from parser.CVisitor import CVisitor
from parser.CLexer import CLexer
from parser.CParser import CParser
from antlr4 import *
import llvmlite.ir as ir
from generator.types import TinyCTypes
from generator.util import *
from generator.errors import *


class TinyCGenerator(CVisitor):
    def __init__(self, error_listener=TinyCErrorListener()):
        self.module = ir.Module()
        self.local_vars = {}  # 局部变量
        self.continue_block = None  # 当调用continue时应该跳转到的语句块
        self.break_block = None  # 当调用break时应该跳转到的语句块
        self.emit_printf()  # 引入printf函数
        self.emit_exit()  # 引入exit函数
        self.current_base_type = None  #当前上下文的基础数据类型
        self.is_global = True  #当前是否处于全局环境中
        self.error_listener = error_listener  #错误监听器

    def emit_printf(self):
        """引入printf函数"""
        printf_type = ir.FunctionType(TinyCTypes.int, (ir.PointerType(TinyCTypes.char),), var_arg=True)
        printf_func = ir.Function(self.module, printf_type, "printf")
        self.local_vars["printf"] = printf_func

    def emit_exit(self):
        """引入exit函数"""
        exit_type = ir.FunctionType(TinyCTypes.void, (TinyCTypes.int, ), var_arg=False)
        exit_func = ir.Function(self.module, exit_type, "exit")
        self.local_vars["exit"] = exit_func

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
        func_name, function_type, arg_names = self.visit(ctx.declarator())  # 获得函数名、函数类型、参数名列表
        llvm_function = ir.Function(self.module, function_type, name=func_name)
        self.builder = ir.IRBuilder(llvm_function.append_basic_block(name="entry"))

        self.local_vars[func_name] = llvm_function

        for arg_name, llvm_arg in zip(arg_names, llvm_function.args):
            self.local_vars[arg_name] = llvm_arg

        self.continue_block = None
        self.break_block = None

        self.visit(ctx.compoundStatement())

        if function_type.return_type == TinyCTypes.void:
            self.builder.ret_void()

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
            |   structOrUnionSpecifier
            |   enumSpecifier
            |   typedefName
            |   typeSpecifier pointer
        :param ctx:
        :return: 对应的LLVM类型
        """
        if match_rule(ctx.children[0], CParser.RULE_typeSpecifier):
            # typeSpecifier pointer
            return ir.PointerType(self.visit(ctx.typeSpecifier()))
        elif match_texts(ctx, TinyCTypes.str2type.keys()):
            # void | char | short | int | long | float | double |
            return TinyCTypes.str2type[ctx.getText()]
        elif match_rule(ctx.children[0], CParser.RULE_typedefName):  # typedefName
            return self.visit(ctx.typedefName())
        else:
            # TODO
            raise NotImplementedError("visitTypeSpecifier")

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
        self.current_base_type = self.visit(ctx.declarationSpecifiers())
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
        if len(ctx.children) == 1:  # Identifier
            return ctx.getText(), self.current_base_type
        elif match_rule(ctx.children[0], CParser.RULE_directDeclarator):
            name, old_type = self.visit(ctx.directDeclarator())
            if ctx.children[1].getText() == '[':
                if match_text(ctx.children[2], ']'):  # directDeclarator '[' ']'
                    new_type = ir.PointerType(old_type)
                else:  # directDeclarator '[' assignmentExpression ']'
                    array_size = int(ctx.children[2].getText())
                    new_type = ir.ArrayType(element=old_type, count=array_size)
                return name, new_type
            elif ctx.children[1].getText() == '(':
                if match_rule(ctx.children[2], CParser.RULE_parameterTypeList):
                    # directDeclarator '(' parameterTypeList ')'
                    arg_names, arg_types = self.visit(ctx.parameterTypeList())  # 获得函数参数的名字列表和类型列表
                    new_type = ir.FunctionType(old_type, arg_types)
                    return name, new_type, arg_names
                elif match_rule(ctx.children[2], CParser.RULE_identifierList):
                    # TODO directDeclarator '(' identifierList ')' 不知道这个是对应什么C语法
                    raise NotImplementedError("directDeclarator '(' identifierList ')'")
                else:
                    # directDeclarator '(' ')'
                    arg_names = []
                    arg_types = []
                    new_type = ir.FunctionType(old_type, arg_types)
                    return name, new_type, arg_names
        else:
            # TODO '(' typeSpecifier? pointer directDeclarator ')'
            raise NotImplementedError("'(' typeSpecifier? pointer directDeclarator ')'")

    def visitAssignmentExpression(self, ctx:CParser.AssignmentExpressionContext):
        """
        assignmentExpression
            :   conditionalExpression
            |   unaryExpression assignmentOperator assignmentExpression
        :param ctx:
        :return: 表达式的值，变量本身
        """
        if match_rule(ctx.children[0], CParser.RULE_conditionalExpression):
            lhs, lhs_ptr = self.visit(ctx.conditionalExpression())
            return lhs, lhs_ptr
        elif match_rule(ctx.children[0], CParser.RULE_unaryExpression):
            lhs, lhs_ptr = self.visit(ctx.unaryExpression())
            op = self.visit(ctx.assignmentOperator())
            rhs, _ = self.visit(ctx.assignmentExpression())
            # TODO 3完善赋值运算符
            if op == '=':
                converted_rhs = TinyCTypes.cast_type(self.builder, value=rhs, target_type=lhs_ptr.type.pointee, ctx=ctx)
                self.builder.store(converted_rhs, lhs_ptr)
                return converted_rhs, None
            else:
                raise NotImplementedError("visitAssignmentExpression")

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
        :return:表达式的值，变量本身
        """
        # TODO 4实现条件表达式
        return self.visit(ctx.logicalOrExpression())

    def visitLogicalOrExpression(self, ctx:CParser.LogicalOrExpressionContext):
        """
        logicalOrExpression
            :   logicalAndExpression
            |   logicalOrExpression '||' logicalAndExpression
            ;
        :param ctx:
        :return:表达式的值，变量本身
        """
        rhs, rhs_ptr = self.visit(ctx.logicalAndExpression())
        if len(ctx.children) == 1:  # logicalAndExpression
            return rhs, rhs_ptr
        else:  # logicalOrExpression '||' logicalAndExpression
            lhs, _ = self.visit(ctx.logicalOrExpression())
            converted_lhs = TinyCTypes.cast_type(self.builder, value=lhs, target_type=TinyCTypes.bool, ctx=ctx)
            converted_rhs = TinyCTypes.cast_type(self.builder, value=rhs, target_type=TinyCTypes.bool, ctx=ctx)
            return self.builder.or_(converted_lhs, converted_rhs), None

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
        if match_rule(ctx.children[0], CParser.RULE_postfixExpression):  # postfixExpression
            return self.visit(ctx.postfixExpression())
        elif match_texts(ctx.children[0], ['++', '--']):  # '++' unaryExpression | '--' unaryExpression
            rhs, rhs_ptr = self.visit(ctx.unaryExpression())
            one = TinyCTypes.int(1)
            if match_text(ctx.children[0], '++'):
                res = self.builder.add(rhs, one)
            else:
                res = self.builder.sub(rhs, one)
            self.builder.store(res, rhs_ptr)
            return res, rhs_ptr
        elif match_rule(ctx.children[0], CParser.RULE_unaryOperator):  #unaryOperator castExpression
            op = self.visit(ctx.unaryOperator())
            rhs, rhs_ptr = self.visit(ctx.castExpression())
            if op == '&':
                return rhs_ptr, None
            elif op == '*':
                return self.builder.load(rhs), rhs
            elif op == '+':
                return rhs, None
            elif op == '-':
                zero = ir.Constant(rhs.type, 0)
                res = self.builder.sub(zero, rhs)
                return res, None
            else:
                # TODO 完善一元运算表达式
                raise NotImplementedError("! and ~ not finished")
        else:
            # TODO 完善一元运算表达式
            raise NotImplementedError("visitUnaryExpression not finished yet.")

    def visitCastExpression(self, ctx:CParser.CastExpressionContext):
        """
        castExpression
            :   '(' typeName ')' castExpression
            |   unaryExpression
            ;
        :param ctx:
        :return: 表达式的值，变量本身
        """
        # TODO 实现类型转换表达式
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
        if match_rule(ctx.children[0], CParser.RULE_primaryExpression):  # primaryExpression
            return self.visit(ctx.primaryExpression())
        elif match_rule(ctx.children[0], CParser.RULE_postfixExpression):
            lhs, lhs_ptr = self.visit(ctx.postfixExpression())
            op = ctx.children[1].getText()
            if op == '[':  # postfixExpression '[' expression ']'
                array_index, _ = self.visit(ctx.expression())
                array_index = TinyCTypes.cast_type(self.builder, target_type=TinyCTypes.int, value=array_index, ctx=ctx)
                zero = ir.Constant(TinyCTypes.int, 0)
                if type(lhs_ptr) is ir.Argument:
                    array_indices = [array_index]
                else:
                    array_indices = [zero, array_index]
                ptr = self.builder.gep(lhs_ptr, array_indices)
                return self.builder.load(ptr), ptr
            elif op == '(':  # postfixExpression '(' argumentExpressionList? ')'
                if len(ctx.children) == 4:
                    args = self.visit(ctx.argumentExpressionList())
                else:
                    args = []
                converted_args = [TinyCTypes.cast_type(self.builder, value=arg, target_type=callee_arg.type, ctx=ctx)
                                  for arg, callee_arg in zip(args, lhs.args)]
                if len(converted_args) < len(args):  # 考虑变长参数
                    converted_args += args[len(lhs.args):]
                return self.builder.call(lhs, converted_args), None
            elif op in ["++", "--"]:
                one = lhs.type(1)
                if op == '++':
                    res = self.builder.add(lhs, one)
                else:
                    res = self.builder.sub(lhs, one)
                self.builder.store(res, lhs_ptr)
                return lhs, lhs_ptr
            else:
                # TODO 实现结构体时需要实现.和->
                raise NotImplementedError(". -> not finished yet.")
        raise NotImplementedError("visitPostfixExpression not finished yet")

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
                            zero = ir.Constant(TinyCTypes.int, 0)
                            var_val = self.builder.gep(var, [zero, zero])
                        else:
                            var_val = self.builder.load(var)
                    return var_val, var
                else:
                    raise SemanticError(ctx=ctx, msg="undefined identifier "+text)
            elif ctx.StringLiteral():
                str_len = len(parse_escape(text[1:-1]))
                return TinyCTypes.get_const_from_str(ir.ArrayType(TinyCTypes.char, str_len+1), const_value=text, ctx=ctx), None
            else:
                # TODO 需要根据text的特点，确定其为浮点数、整数还是字符(目前的策略比较简单)
                if '.' in text:  # 浮点数
                    const_value = TinyCTypes.get_const_from_str(TinyCTypes.double, text, ctx=ctx)
                elif text.startswith("'"):  # 字符
                    const_value = TinyCTypes.get_const_from_str(TinyCTypes.char, text, ctx=ctx)
                else:  # 整数
                    const_value = TinyCTypes.get_const_from_str(TinyCTypes.int, text, ctx=ctx)
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
        arg, _ = self.visit(ctx.assignmentExpression())
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
                ret_val, _ = self.visit(ctx.expression())
                converted_val = TinyCTypes.cast_type(
                    self.builder, target_type=self.builder.function.type.pointee.return_type, value=ret_val, ctx=ctx)
                self.builder.ret(converted_val)
            else:
                self.builder.ret_void()
        elif jump_str == 'continue':
            self.builder.branch(self.continue_block)
        elif jump_str == 'break':
            self.builder.branch(self.break_block)
        else:
            # TODO 尚未支持goto语句
            raise NotImplementedError("goto")

    def visitMultiplicativeExpression(self, ctx:CParser.MultiplicativeExpressionContext):
        """
        multiplicativeExpression
            :   castExpression
            |   multiplicativeExpression '*' castExpression
            |   multiplicativeExpression '/' castExpression
            |   multiplicativeExpression '%' castExpression
            ;
        :param ctx:
        :return: 表达式的值,变量本身
        """
        rhs, rhs_ptr = self.visit(ctx.castExpression())
        if match_rule(ctx.children[0], CParser.RULE_castExpression):
            return rhs, rhs_ptr
        else:
            lhs, lhs_ptr = self.visit(ctx.multiplicativeExpression())
            converted_target = lhs.type
            converted_rhs = TinyCTypes.cast_type(self.builder, value=rhs, target_type=converted_target, ctx=ctx)  # 将rhs转成lhs的类型
            op = ctx.children[1].getText()
            if TinyCTypes.is_int(converted_target): # 整数运算
                if op == '*':
                    return self.builder.mul(lhs, converted_rhs), None
                elif op == '/':
                    return self.builder.sdiv(lhs, converted_rhs), None
                else:
                    return self.builder.srem(lhs, converted_rhs), None
            elif TinyCTypes.is_float(converted_target):  #浮点数运算
                if op == '*':
                    return self.builder.fmul(lhs, converted_rhs), None
                elif op == '/':
                    return self.builder.fdiv(lhs, converted_rhs), None
                else:
                    raise SemanticError(ctx=ctx, msg="Float doesn't support % operation")
            else:
                raise SemanticError(ctx=ctx, msg="Illegal operation: "+str(lhs)+op+str(rhs))

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
            if isinstance(init_val, list):  # 如果初始值是一个列表
                converted_val = ir.Constant(var_type, init_val)
            else:  # 如果初始值是一个值
                if isinstance(var_type, ir.PointerType) and isinstance(init_val.type, ir.ArrayType) and var_type.pointee == init_val.type.element:
                    var_type = init_val.type  # 数组赋值给指针，不需要进行强制转换
                converted_val = TinyCTypes.cast_type(self.builder, value=init_val, target_type=var_type, ctx=ctx)
            # TODO 目前多维数组初始化必须使用嵌套的方式，并且无法自动补零
            # TODO 数组变量初始化时，未能自动进行类型转换

        if self.is_global:  #如果是全局变量
            self.local_vars[var_name] = ir.GlobalVariable(self.module, var_type, name=var_name)
            self.local_vars[var_name].linkage = "internal"
            if len(ctx.children) == 3:
                self.local_vars[var_name].initializer = converted_val
        else:  #如果是局部变量
            self.local_vars[var_name] = self.builder.alloca(var_type)
            if len(ctx.children) == 3:
                self.builder.store(converted_val, self.local_vars[var_name])

    def visitInitializer(self, ctx:CParser.InitializerContext):
        """
        initializer
            :   assignmentExpression
            |   '{' initializerList '}'
            |   '{' initializerList ',' '}'
            ;
        :param ctx:
        :return:
        """
        if len(ctx.children) == 1:
            value, _ = self.visit(ctx.assignmentExpression())
            return value
        else:
            return self.visit(ctx.initializerList())

    def visitInitializerList(self, ctx:CParser.InitializerListContext):
        """
        initializerList
            :   initializer
            |   initializerList ',' initializer
            ;
        :param ctx:
        :return: 初始化值的列表
        """
        if len(ctx.children) == 1:
            init_list = []
        else:
            init_list = self.visit(ctx.initializerList())
        init_list.append(self.visit(ctx.initializer()))
        return init_list

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
            # TODO do-while循环
            raise NotImplementedError("do while")

        self.builder.branch(cond_block)
        self.builder.position_at_start(cond_block)
        if cond_expression:
            cond_val, _ = self.visit(cond_expression)
            converted_cond_val = TinyCTypes.cast_type(self.builder, target_type=TinyCTypes.bool, value=cond_val, ctx=ctx)
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
        if match_rule(ctx.children[idx], CParser.RULE_forDeclaration):
            idx += 2
            self.visit(ctx.forDeclaration())
        elif match_rule(ctx.children[idx], CParser.RULE_expression):
            idx += 2
            self.visit(ctx.expression())
        else:
            idx += 1

        cond_expression = None
        update_expression = None
        if match_rule(ctx.children[idx], CParser.RULE_forExpression):
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
            cond_val, _ = self.visit(ctx.expression())
            converted_cond_val = TinyCTypes.cast_type(self.builder, target_type=TinyCTypes.bool, value=cond_val, ctx=ctx)
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
            # TODO switch
            raise NotImplementedError("switch not finishe yet")

    def visitAdditiveExpression(self, ctx:CParser.AdditiveExpressionContext):
        """
        additiveExpression
            :   multiplicativeExpression
            |   additiveExpression '+' multiplicativeExpression
            |   additiveExpression '-' multiplicativeExpression
            ;
        :param ctx:
        :return:
        """
        rhs, rhs_ptr = self.visit(ctx.multiplicativeExpression())
        if len(ctx.children) == 1:  # multiplicativeExpression
            return rhs, rhs_ptr
        else:
            lhs, _ = self.visit(ctx.additiveExpression())
            op = ctx.children[1].getText()
            convert_target = lhs.type
            converted_rhs = TinyCTypes.cast_type(self.builder, value=rhs, target_type=convert_target, ctx=ctx)
            if TinyCTypes.is_int(convert_target):
                if op == '+':
                    return self.builder.add(lhs, converted_rhs), None
                else:
                    return self.builder.sub(lhs, converted_rhs), None
            elif TinyCTypes.is_float(convert_target):
                if op == '+':
                    return self.builder.fadd(lhs, converted_rhs), None
                else:
                    return self.builder.fsub(lhs, converted_rhs), None
            else:
                raise SemanticError(ctx=ctx, msg="Illegal operation: "+str(lhs)+op+str(rhs))

    def _visitRelatioinAndEqualityExpression(self, ctx):
        """
        由于visitRelationalExpression和visitEqualityExpression的处理过程非常相像，
        因此将它们的处理过程抽离成一个函数
        :param ctx:
        :return:
        """
        rhs, rhs_ptr = self.visit(ctx.children[-1])
        if len(ctx.children) == 1:
            return rhs, rhs_ptr
        else:
            lhs, _ = self.visit(ctx.children[0])
            op = ctx.children[1].getText()
            converted_target = lhs.type
            converted_rhs = TinyCTypes.cast_type(self.builder, value=rhs, target_type=converted_target, ctx=ctx)
            if TinyCTypes.is_int(converted_target):
                return self.builder.icmp_signed(cmpop=op, lhs=lhs, rhs=converted_rhs), None
            elif TinyCTypes.is_float(converted_target):
                return self.builder.fcmp_ordered(cmpop=op, lhs=lhs, rhs=converted_rhs), None
            else:
                raise SemanticError(ctx=ctx, msg="Unknown relation expression: " + str(lhs) + str(op) + str(rhs))

    def visitRelationalExpression(self, ctx:CParser.RelationalExpressionContext):
        """
        relationalExpression
            :   shiftExpression
            |   relationalExpression '<' shiftExpression
            |   relationalExpression '>' shiftExpression
            |   relationalExpression '<=' shiftExpression
            |   relationalExpression '>=' shiftExpression
            ;
        :param ctx:
        :return:
        """
        return self._visitRelatioinAndEqualityExpression(ctx)

    def visitEqualityExpression(self, ctx:CParser.EqualityExpressionContext):
        """
        equalityExpression
            :   relationalExpression
            |   equalityExpression '==' relationalExpression
            |   equalityExpression '!=' relationalExpression
            ;
        :param ctx:
        :return:
        """
        return self._visitRelatioinAndEqualityExpression(ctx)

    def visitLogicalAndExpression(self, ctx:CParser.LogicalAndExpressionContext):
        """
        logicalAndExpression
            :   inclusiveOrExpression
            |   logicalAndExpression '&&' inclusiveOrExpression
            ;
        :param ctx:
        :return:
        """
        rhs, rhs_ptr = self.visit(ctx.inclusiveOrExpression())
        if len(ctx.children) == 1:
            return rhs, rhs_ptr
        else:
            lhs, _ = self.visit(ctx.logicalAndExpression())
            converted_lhs = TinyCTypes.cast_type(self.builder, value=lhs, target_type=TinyCTypes.bool, ctx=ctx)
            converted_rhs = TinyCTypes.cast_type(self.builder, value=rhs, target_type=TinyCTypes.bool, ctx=ctx)
            return self.builder.and_(converted_lhs, converted_rhs), None

    def visitBlockItem(self, ctx:CParser.BlockItemContext):
        """
        blockItem
            :   statement
            |   declaration
            ;
        以blockItem为单位进行语义报错
        :param ctx:
        :return:
        """
        try:
            self.visit(ctx.children[0])
        except SemanticError as e:
            self.error_listener.register_semantic_error(e)

    def visitExternalDeclaration(self, ctx:CParser.ExternalDeclarationContext):
        """
        externalDeclaration
            :   functionDefinition
            |   declaration
            |   ';' // stray ;
            ;
        以externalDeclaration为单位进行语义报错
        :param ctx:
        :return:
        """
        if not match_text(ctx.children[0], ","):
            try:
                self.visit(ctx.children[0])
            except SemanticError as e:
                self.error_listener.register_semantic_error(e)

    def save(self, filename):
        """保存到文件"""
        with open(filename, "w") as f:
            f.write(repr(self.module))


def generate(input_filename, output_filename):
    """
    将C代码文件转成IR代码文件
    :param input_filename: C代码文件
    :param output_filename: IR代码文件
    :return: 生成是否成功
    """
    lexer = CLexer(FileStream(input_filename))
    stream = CommonTokenStream(lexer)
    parser = CParser(stream)

    error_listener = TinyCErrorListener()
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)

    tree = parser.compilationUnit()

    generator = TinyCGenerator(error_listener)
    generator.visit(tree)
    generator.save(output_filename)

    if len(error_listener.errors) == 0:
        return True
    else:
        error_listener.print_errors()
        return False



