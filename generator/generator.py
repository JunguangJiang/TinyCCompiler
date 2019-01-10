from parser_.CVisitor import CVisitor
from parser_.CLexer import CLexer
from parser_.CParser import CParser
from antlr4 import *
import llvmlite.ir as ir
from generator.types import TinyCTypes
from generator.util import *
from generator.errors import *
from generator.symbol_table import SymbolTable, RedefinitionError


class TinyCGenerator(CVisitor):
    def __init__(self, error_listener=TinyCErrorListener()):
        self.module = ir.Module()
        self.builder = ir.IRBuilder()
        self.symbol_table = SymbolTable()  # 符号表
        self.continue_block = None  # 当调用continue时应该跳转到的语句块
        self.break_block = None  # 当调用break时应该跳转到的语句块
        self.switch_context = None  # TODO
        self.emit_printf()  # 引入printf函数
        self.emit_exit()  # 引入exit函数
        self.current_base_type = None  #当前上下文的基础数据类型
        self.is_global = True  #当前是否处于全局环境中
        self.error_listener = error_listener  #错误监听器
        self.global_context = ir.global_context
        self.struct_reflection = {}
        self.is_defining_struct = ''

    def emit_printf(self):
        """引入printf函数"""
        printf_type = ir.FunctionType(TinyCTypes.int, (ir.PointerType(TinyCTypes.char),), var_arg=True)
        printf_func = ir.Function(self.module, printf_type, "printf")
        self.symbol_table["printf"] = printf_func

    def emit_exit(self):
        """引入exit函数"""
        exit_type = ir.FunctionType(TinyCTypes.void, (TinyCTypes.int, ), var_arg=False)
        exit_func = ir.Function(self.module, exit_type, "exit")
        self.symbol_table["exit"] = exit_func

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
            declaratorList = self.visit(ctx.initDeclaratorList())

            if declaratorList is not None and len(declaratorList) == 3:  #说明是函数声明
                func_name, function_type, arg_names = declaratorList  # 获得函数名、函数类型、参数名列表
                llvm_function = ir.Function(self.module, function_type, name=func_name)
                if func_name not in self.symbol_table:  # 允许函数重复声明
                    self.symbol_table[func_name] = llvm_function

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
        if func_name in self.symbol_table:
            # TODO 此处尚未检查函数定义和声明是否参数一致
            llvm_function = self.symbol_table[func_name]
        else:
            llvm_function = ir.Function(self.module, function_type, name=func_name)
            self.symbol_table[func_name] = llvm_function
        self.builder = ir.IRBuilder(llvm_function.append_basic_block(name="entry"))

        self.symbol_table.enter_scope()
        try:
            for arg_name, llvm_arg in zip(arg_names, llvm_function.args):
                self.symbol_table[arg_name] = llvm_arg
        except RedefinitionError as e:
            raise SemanticError(msg="Redefinition local variable {}".format(arg_name), ctx=ctx)

        self.continue_block = None
        self.break_block = None

        self.visit(ctx.compoundStatement())

        if function_type.return_type == TinyCTypes.void:
            self.builder.ret_void()
        self.symbol_table.exit_scope()
        self.is_global = True

    def visitTypedefName(self, ctx:CParser.TypedefNameContext):
        """
            typedefName
        :   Identifier
        ;
        :param ctx:
        :return:
        """
        return ctx.getText()

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
        elif match_rule(ctx.children[0], CParser.RULE_structOrUnionSpecifier):
            return self.visit(ctx.structOrUnionSpecifier())
        else:
            raise NotImplementedError("visitTypeSpecifier")

    def visitStructOrUnion(self, ctx:CParser.StructOrUnionContext):
        """
        structOrUnion
            :   'struct'
            | 'union'
        :param ctx:
        :return: 'struct' or 'union'
        """
        return ctx.getText()

    def visitSpecifierQualifierList(self, ctx:CParser.SpecifierQualifierListContext):
        """
            specifierQualifierList
        :   typeSpecifier specifierQualifierList?
        |   typeQualifier specifierQualifierList?
        ;
        :param ctx:
        :return:
        """
        if ctx.typeQualifier():
            raise NotImplementedError("Not support typeQualifier yet,")
        if len(ctx.children) == 1:
            return self.visit(ctx.children[0])
        else:
            sub_dict = {'type': self.visit(ctx.children[0]),
                        'name': self.visit(ctx.children[1])}
            return sub_dict

    def visitStructDeclaration(self, ctx:CParser.StructDeclarationContext):
        """
            structDeclaration
        :   specifierQualifierList structDeclaratorList? ';'
        |   staticAssertDeclaration
        ;
        :param ctx:
        :return: a tuple of reflection between name and index
        """
        # 只支持第一种不带structDeclaratorList的格式
        if ctx.staticAssertDeclaration() or ctx.structDeclaratorList():
            raise NotImplementedError("Not support complex struct declaration.")
        return self.visit(ctx.specifierQualifierList())


    def visitStructDeclarationList(self, ctx:CParser.StructDeclarationListContext):
        """
            structDeclarationList
        :   structDeclaration
        |   structDeclarationList structDeclaration
        ;
        :param ctx:
        :return: a list contains the element's type(value) and element's name(key)
        """
        if len(ctx.children) == 2:
            sub_list = self.visit(ctx.structDeclarationList())
            sub_dict = self.visit(ctx.structDeclaration())
            sub_list.append(sub_dict)
            return sub_list
        else:
            sub_dict = self.visit(ctx.structDeclaration())
            return [sub_dict]

    def visitStructOrUnionSpecifier(self, ctx:CParser.StructOrUnionSpecifierContext):
        """
        structOrUnionSpecifier
            :   structOrUnion Identifier? '{' structDeclarationList '}'
            | structOrUnion Identifier
            ;
        :param ctx:
        :return: LLVM struct type
        """
        if len(ctx.children) >= 4:  # 结构本身的声明/定义
            s_or_u = self.visit(ctx.structOrUnion())
            if s_or_u == 'struct':  # 结构
                if(len(ctx.children) == 5):  # 非匿名结构
                    if ctx.Identifier().getText() in self.struct_reflection.keys():
                        # 重定义
                        raise SemanticError(ctx=ctx, msg="Struct" + ctx.Identifier().getText() + "Redefinition")
                    else:
                        struct_name = ctx.Identifier().getText()
                        self.is_defining_struct = struct_name
                        tmp_list = self.visit(ctx.structDeclarationList())
                        self.struct_reflection[struct_name] = {}
                        index = 0
                        ele_list = []
                        for ele in tmp_list:
                            self.struct_reflection[struct_name][ele['name']] = {
                                'type': ele['type'],
                                'index': index
                            }
                            ele_list.append(ele['type'])
                            index = index + 1
                        new_struct = self.global_context.get_identified_type(name=struct_name)
                        new_struct.set_body(*ele_list)
                        self.is_defining_struct = ''
                        return new_struct
                else:
                    raise NotImplementedError("Anonymous struct is not supported yet.")
            else:
                raise NotImplementedError("Union is not supported yet.")
        else:  # 结构实体的定义
            s_or_u = self.visit(ctx.structOrUnion())
            if s_or_u == 'struct':  # 结构
                struct_name = ctx.Identifier().getText()
                if (ctx.Identifier().getText() in self.struct_reflection.keys()) or self.is_defining_struct == struct_name:
                    # 已有定义或者正在定义该结构
                    new_struct = self.global_context.get_identified_type(name=struct_name)
                    return new_struct
                else:
                    # 未定义结构
                    raise SemanticError(ctx=ctx, msg="Struct " + ctx.Identifier().getText() + " Undefined")
            else:
                raise NotImplementedError("Union is not supported yet.")
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
            elif op == '+=':
                target_type = lhs_ptr.type.pointee
                converted_rhs = TinyCTypes.cast_type(self.builder, value=rhs, target_type=target_type, ctx=ctx)
                if TinyCTypes.is_int(target_type):
                    new_value = self.builder.add(lhs, converted_rhs)
                elif TinyCTypes.is_float(target_type):
                    new_value = self.builder.fadd(lhs, converted_rhs)
                self.builder.store(new_value, lhs_ptr)
                return new_value, None
            elif op == '-=':
                target_type = lhs_ptr.type.pointee
                converted_rhs = TinyCTypes.cast_type(self.builder, value=rhs, target_type=target_type, ctx=ctx)
                if TinyCTypes.is_int(target_type):
                    new_value = self.builder.sub(lhs, converted_rhs)
                elif TinyCTypes.is_float(target_type):
                    new_value = self.builder.fsub(lhs, converted_rhs)
                self.builder.store(new_value, lhs_ptr)
                return new_value, None
            elif op == '*=':
                target_type = lhs_ptr.type.pointee
                converted_rhs = TinyCTypes.cast_type(self.builder, value=rhs, target_type=target_type, ctx=ctx)
                if TinyCTypes.is_int(target_type):
                    new_value = self.builder.mul(lhs, converted_rhs)
                elif TinyCTypes.is_float(target_type):
                    new_value = self.builder.fmul(lhs, converted_rhs)
                self.builder.store(new_value, lhs_ptr)
                return new_value, None
            elif op == '/=':
                target_type = lhs_ptr.type.pointee
                converted_rhs = TinyCTypes.cast_type(self.builder, value=rhs, target_type=target_type, ctx=ctx)
                if TinyCTypes.is_int(target_type):
                    new_value = self.builder.sdiv(lhs, converted_rhs)
                elif TinyCTypes.is_float(target_type):
                    new_value = self.builder.fdiv(lhs, converted_rhs)
                self.builder.store(new_value, lhs_ptr)
                return new_value, None
            elif op == '%=':
                target_type = lhs_ptr.type.pointee
                converted_rhs = TinyCTypes.cast_type(self.builder, value=rhs, target_type=target_type, ctx=ctx)
                if TinyCTypes.is_int(target_type):
                    new_value = self.builder.srem(lhs, converted_rhs)
                elif TinyCTypes.is_float(target_type):
                    raise SemanticError(ctx=ctx, msg="Float doesn't support % operation")
                self.builder.store(new_value, lhs_ptr)
                return new_value, None
            elif op == '<<=':
                target_type = lhs_ptr.type.pointee
                converted_rhs = TinyCTypes.cast_type(self.builder, value=rhs, target_type=target_type, ctx=ctx)
                if TinyCTypes.is_int(target_type):
                    new_value = self.builder.shl(lhs, converted_rhs)
                elif TinyCTypes.is_float(target_type):
                    raise SemanticError(ctx=ctx, msg="Float doesn't support % operation")
                self.builder.store(new_value, lhs_ptr)
                return new_value, None
            elif op == '>>=':
                target_type = lhs_ptr.type.pointee
                converted_rhs = TinyCTypes.cast_type(self.builder, value=rhs, target_type=target_type, ctx=ctx)
                if TinyCTypes.is_int(target_type):
                    new_value = self.builder.ashr(lhs, converted_rhs)
                elif TinyCTypes.is_float(target_type):
                    raise SemanticError(ctx=ctx, msg="Float doesn't support % operation")
                self.builder.store(new_value, lhs_ptr)
                return new_value, None
            elif op == '|=':
                target_type = lhs_ptr.type.pointee
                converted_rhs = TinyCTypes.cast_type(self.builder, value=rhs, target_type=target_type, ctx=ctx)
                if TinyCTypes.is_int(target_type):
                    new_value = self.builder.or_(lhs, converted_rhs)
                elif TinyCTypes.is_float(target_type):
                    raise SemanticError(ctx=ctx, msg="Float doesn't support % operation")
                self.builder.store(new_value, lhs_ptr)
                return new_value, None
            elif op == '&=':
                target_type = lhs_ptr.type.pointee
                converted_rhs = TinyCTypes.cast_type(self.builder, value=rhs, target_type=target_type, ctx=ctx)
                if TinyCTypes.is_int(target_type):
                    new_value = self.builder.and_(lhs, converted_rhs)
                elif TinyCTypes.is_float(target_type):
                    raise SemanticError(ctx=ctx, msg="Float doesn't support % operation")
                self.builder.store(new_value, lhs_ptr)
                return new_value, None
            elif op == '^=':
                target_type = lhs_ptr.type.pointee
                converted_rhs = TinyCTypes.cast_type(self.builder, value=rhs, target_type=target_type, ctx=ctx)
                if TinyCTypes.is_int(target_type):
                    new_value = self.builder.xor(lhs, converted_rhs)
                elif TinyCTypes.is_float(target_type):
                    raise SemanticError(ctx=ctx, msg="Float doesn't support % operation")
                self.builder.store(new_value, lhs_ptr)
                return new_value, None
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
        if ctx.expression() is None:
            return self.visit(ctx.logicalOrExpression())
        cond_val, _ = self.visit(ctx.logicalOrExpression())
        converted_cond_val = TinyCTypes.cast_type(self.builder, target_type=TinyCTypes.bool, value=cond_val, ctx=ctx)
        # TODO type cast
        true_val, _ = self.visit(ctx.expression())
        false_val, _ = self.visit(ctx.conditionalExpression())
        ret_pointer = self.builder.alloca(true_val.type)
        with self.builder.if_else(converted_cond_val) as (then, otherwise):
            with then:
                self.builder.store(true_val, ret_pointer)
            with otherwise:
                self.builder.store(false_val, ret_pointer)
        ret_val = self.builder.load(ret_pointer)
        return ret_val, None

    def visitLogicalOrExpression(self, ctx:CParser.LogicalOrExpressionContext):
        """
        logicalOrExpression
            :   logicalAndExpression
            |   logicalOrExpression '||' logicalAndExpression
            ;
        :param ctx:
        :return:表达式的值，变量本身
        """
        if len(ctx.children) == 1:  # logicalAndExpression
            rhs, rhs_ptr = self.visit(ctx.logicalAndExpression())
            return rhs, rhs_ptr
        else:  # logicalOrExpression '||' logicalAndExpression
            lhs, _ = self.visit(ctx.logicalOrExpression())
            converted_lhs = TinyCTypes.cast_type(self.builder, value=lhs, target_type=TinyCTypes.bool, ctx=ctx)
            result = self.builder.alloca(TinyCTypes.bool)
            with self.builder.if_else(converted_lhs) as (then, otherwise):
                with then:
                    self.builder.store(TinyCTypes.bool(1), result)
                with otherwise:
                    rhs, rhs_ptr = self.visit(ctx.logicalAndExpression())
                    converted_rhs = TinyCTypes.cast_type(self.builder, value=rhs, target_type=TinyCTypes.bool, ctx=ctx)
                    self.builder.store(converted_rhs, result)
            return self.builder.load(result), None

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
            elif op == '!':
                origin = TinyCTypes.cast_type(self.builder, TinyCTypes.int, rhs, ctx)
                zero = TinyCTypes.int(0)
                res = self.builder.icmp_signed("==", zero, origin)
                res = self.builder.zext(res, TinyCTypes.int)
                return res, None
            elif op == '~':
                if TinyCTypes.is_int(rhs.type):
                    res = self.builder.not_(rhs)
                    return res, None
                else:
                    raise SemanticError(ctx=ctx, msg="Wrong type argument to bit-complement.")
            else:
                raise SemanticError(ctx=ctx, msg="Should not reach here.")
        else:
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
            elif op == '.':
                # TODO 实现结构体时需要实现.和->
                '''
                print('>>>>>>>>>>>>>>>')
                print(lhs)
                print(type(lhs.type))
                print(lhs.name)
                print(lhs_ptr)
                print(type(lhs_ptr.type))
                print(type(lhs_ptr.value_type))
                print(lhs_ptr.name)
                print('<<<<<<<<<<<<<<')'''
                ele_name = ctx.Identifier().getText()
                '''
                print(lhs_ptr.value_type.name)
                print(lhs_ptr.value_type)
                '''
                print('==============')
                print(lhs_ptr.type.pointee.name)
                print(lhs_ptr)
                print(type(lhs_ptr.type))
                #target_name = lhs_ptr.value_type.name
                target_name = lhs_ptr.type.pointee.name
                print("target_name="+target_name)
                print("============")
                array_index = self.struct_reflection[target_name][ele_name]['index']
                array_index = ir.Constant(TinyCTypes.int, array_index)
                zero = ir.Constant(TinyCTypes.int, 0)
                array_indices = [zero, array_index]
                ptr = self.builder.gep(lhs_ptr, array_indices)
                print('[[[[[[[[[[[[[[[')
                print(ptr)
                print(ptr.type)
                print(type(ptr.type))
                return self.builder.load(ptr), ptr
            else:
                ele_name = ctx.Identifier().getText()
                target_name = lhs.type.pointee.name
                print('-=-=-=-=-=-=')
                print(type(lhs.type.pointee))
                if type(lhs.type.pointee) != ir.IdentifiedStructType:
                    print("OVER")
                    print(type(lhs.type.pointee))
                    print(ir.IdentifiedStructType)
                    print("OOOO")
                    raise SemanticError(ctx=ctx, msg="Illegal operation on -> operator.")
                array_index = self.struct_reflection[target_name][ele_name]['index']
                array_index = ir.Constant(TinyCTypes.int, array_index)
                zero = ir.Constant(TinyCTypes.int, 0)
                array_indices = [zero, array_index]
                ptr = self.builder.gep(lhs, array_indices)
                return self.builder.load(ptr), ptr
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
                if text in self.symbol_table:
                    var = self.symbol_table[text]
                    if type(var) in [ir.Argument, ir.Function]:
                        var_val = var
                    else:
                        if isinstance(var.type.pointee, ir.ArrayType) or isinstance(var.type.pointee, ir.IdentifiedStructType):
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

    def visitInitDeclaratorList(self, ctx:CParser.InitDeclaratorListContext):
        """
        initDeclaratorList
            :   initDeclarator
            |   initDeclaratorList ',' initDeclarator
            ;
        :param ctx:
        :return:
        """
        if len(ctx.children) == 3:
            self.visit(ctx.initDeclaratorList())
        declarator = self.visit(ctx.initDeclarator())
        return declarator

    def visitInitDeclarator(self, ctx:CParser.InitDeclaratorContext):
        """
        initDeclarator
            :   declarator
            |   declarator '=' initializer
            ;
        :param ctx:
        :return:
        """
        declarator = self.visit(ctx.declarator())
        if len(declarator) == 3:  # 函数定义的变量列表
            return declarator
        else:
            var_name, var_type = declarator
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
            try:
                if self.is_global:  #如果是全局变量
                    self.symbol_table[var_name] = ir.GlobalVariable(self.module, var_type, name=var_name)
                    self.symbol_table[var_name].linkage = "internal"
                    if len(ctx.children) == 3:
                        self.symbol_table[var_name].initializer = converted_val
                else:  #如果是局部变量
                    self.symbol_table[var_name] = self.builder.alloca(var_type)
                    if len(ctx.children) == 3:
                        self.builder.store(converted_val, self.symbol_table[var_name])
            except RedefinitionError as e:
                raise SemanticError(msg="redefinition variable {}".format(var_name), ctx=ctx)

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
        self.symbol_table.enter_scope()
        name_prefix = self.builder.block.name
        do_block = self.builder.append_basic_block(name=name_prefix + "loop_do")  # do语句块，先跑一遍
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
        elif iteration_type == "do":  # do while
            cond_expression = ctx.expression()
        else:
            raise SemanticError(ctx=ctx, msg="Cannot recognize loop form!")
        self.builder.branch(do_block)
        self.builder.position_at_start(do_block)
        if iteration_type == "do":
            self.visit(ctx.statement())
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
        self.symbol_table.exit_scope()

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
            self.symbol_table.enter_scope()
            if len(statements) == 2:  # 存在else分支
                with self.builder.if_else(converted_cond_val) as (then, otherwise):
                    with then:
                        self.visit(statements[0])
                    with otherwise:
                        self.visit(statements[1])
            else:  # 只有if分支
                with self.builder.if_then(converted_cond_val):
                    self.visit(statements[0])
            self.symbol_table.exit_scope()
        else:
            name_prefix = self.builder.block.name
            start_block = self.builder.block
            end_block = self.builder.append_basic_block(name=name_prefix + '.end_switch')
            old_context = self.switch_context
            old_break = self.break_block
            self.break_block = end_block
            cond_val, _ = self.visit(ctx.expression())
            self.switch_context = [[], None, name_prefix + '.case.']
            self.visit(ctx.statement(0))
            try:
                self.builder.branch(end_block)
            except AssertionError:
                # 最后一个标签里有break或return语句，不用跳转
                pass
            label_blocks = []
            for i in range(len(self.switch_context[0])):
                label_blocks.append(self.builder.append_basic_block(name=name_prefix + '.label.' + str(i)))
            self.builder.position_at_end(start_block)
            self.builder.branch(label_blocks[0])
            for i, (label, _block) in enumerate(self.switch_context[0]):
                self.builder.position_at_end(label_blocks[i])
                if isinstance(label, str):
                    self.builder.branch(_block)
                else:
                    constant, _ = self.visit(label)
                    condition = self.builder.icmp_signed(cmpop='==', lhs=cond_val, rhs=constant)
                    if i == len(self.switch_context[0]) - 1:
                        false_block = end_block
                    else:
                        false_block = label_blocks[i + 1]
                    self.builder.cbranch(condition, _block, false_block)
            self.builder.position_at_start(end_block)
            self.switch_context = old_context
            self.break_block = old_break

    def visitLabeledStatement(self, ctx:CParser.LabeledStatementContext):
        """
        labeledStatement
            :   Identifier ':' statement
            |   'case' constantExpression ':' statement
            |   'default' ':' statement
            ;
        :param ctx:
        :return:
        """
        if ctx.children[0].getText() == 'Identifier':
            raise NotImplementedError('Identifier label is not implemented yet.')
        if len(ctx.children) == 4:
            block_name, label = self.switch_context[2] + str(len(self.switch_context[0])),  ctx.constantExpression()
        else:
            block_name, label = self.switch_context[2] + 'default', 'default'
        content_block = self.builder.append_basic_block(name=block_name)
        self.builder.position_at_end(content_block)
        if self.switch_context[1] is not None:
            cur_block = self.builder.block
            self.builder.position_at_end(self.switch_context[1])
            try:
                self.builder.branch(cur_block)
            except AssertionError:
                # 上一个分支有return或break语句时不用跳到当前分支
                pass
            self.builder.position_at_end(cur_block)
        self.switch_context[1] = self.builder.block
        self.visit(ctx.statement())
        self.switch_context[0].append((label, content_block))

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

    def visitShiftExpression(self, ctx:CParser.ShiftExpressionContext):
        """
        shiftExpression
            :   additiveExpression
            |   shiftExpression '<<' additiveExpression
            |   shiftExpression '>>' additiveExpression
            ;
        :param ctx:
        :return:
        """
        rhs, rhs_ptr = self.visit(ctx.additiveExpression())
        if len(ctx.children) == 1:
            return rhs, rhs_ptr
        else:
            lhs, _ = self.visit(ctx.shiftExpression())
            if ctx.children[1].getText() == '<<':
                return self.builder.shl(lhs, rhs), None
            else:
                return self.builder.ashr(lhs, rhs), None


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
        if len(ctx.children) == 1:
            rhs, rhs_ptr = self.visit(ctx.inclusiveOrExpression())
            return rhs, rhs_ptr
        else:
            lhs, _ = self.visit(ctx.logicalAndExpression())
            converted_lhs = TinyCTypes.cast_type(self.builder, value=lhs, target_type=TinyCTypes.bool, ctx=ctx)
            result = self.builder.alloca(TinyCTypes.bool)
            with self.builder.if_else(converted_lhs) as (then, otherwise):
                with then:
                    rhs, rhs_ptr = self.visit(ctx.inclusiveOrExpression())
                    converted_rhs = TinyCTypes.cast_type(self.builder, value=rhs, target_type=TinyCTypes.bool, ctx=ctx)
                    self.builder.store(converted_rhs, result)
                with otherwise:
                    self.builder.store(TinyCTypes.bool(0), result)
            return self.builder.load(result), None

    def visitInclusiveOrExpression(self, ctx: CParser.InclusiveOrExpressionContext):
        """
        inclusiveOrExpression
            :   exclusiveOrExpression
            |   inclusiveOrExpression '|' exclusiveOrExpression
            ;
        :param ctx:
        :return:
        """
        rhs, rhs_ptr = self.visit(ctx.exclusiveOrExpression())
        if len(ctx.children) == 1:
            return rhs, rhs_ptr
        else:
            lhs, _ = self.visit(ctx.inclusiveOrExpression())
            return self.builder.or_(lhs, rhs), None

    def visitExclusiveOrExpression(self, ctx:CParser.ExclusiveOrExpressionContext):
        """
        exclusiveOrExpression
            :   andExpression
            |   exclusiveOrExpression '^' andExpression
            ;
        :param ctx:
        :return:
        """
        rhs, rhs_ptr = self.visit(ctx.andExpression())
        if len(ctx.children) == 1:
            return rhs, rhs_ptr
        else:
            lhs, _ = self.visit(ctx.exclusiveOrExpression())
            return self.builder.xor(lhs, rhs), None

    def visitAndExpression(self, ctx:CParser.AndExpressionContext):
        """
        andExpression
            :   equalityExpression
            |   andExpression '&' equalityExpression
            ;
        :param ctx:
        :return:
        """
        rhs, rhs_ptr = self.visit(ctx.equalityExpression())
        if len(ctx.children) == 1:
            return rhs, rhs_ptr
        else:
            lhs, _ = self.visit(ctx.andExpression())
            return self.builder.and_(lhs, rhs), None

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



