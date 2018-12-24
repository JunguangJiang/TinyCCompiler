import llvmlite.ir as ir
from generator.util import parse_escape
from generator.errors import SemanticError


class LLVMTypes(object):
    int = ir.IntType(32)
    short = ir.IntType(16)
    char = ir.IntType(8)
    bool = ir.IntType(1)
    float = ir.FloatType()
    double = ir.DoubleType()
    void = ir. VoidType()
    str2type = {
        "int": int,
        "short": short,
        "char": char,
        "long": int,
        "bool": bool,
        "float": float,
        "double": double,
        "void": void
    }

    @staticmethod
    def get_array_type(elem_type, count):
        """
        获得数组类型
        :param elem_type: 元素的类型
        :param count: 数组大小
        :return:
        """
        return ir.ArrayType(element=elem_type, count=count)

    @staticmethod
    def get_pointer_type(pointee_type):
        """
        获得指针类型
        :param pointee_type: 指向的元素的类型
        :return:
        """
        return ir.PointerType(pointee=pointee_type)

    @classmethod
    def get_const_from_str(cls, llvm_type, const_value, ctx):
        """
        从字符串获得常数类型
        :param llvm_type: 类型,接受char,float,double,short,int,ir.ArrayType
        :param const_value: 值，是一个字符串
        :return:
        """
        if type(const_value) is str:
            if llvm_type == cls.char:
                if len(const_value) > 1:
                    return cls.char(ord(const_value[1]))
                else:
                    return cls.char(int(const_value))
            elif llvm_type in [cls.float, cls.double]:
                return llvm_type(float(const_value))
            elif llvm_type in [cls.short, cls.int]:
                return llvm_type(int(const_value))
            elif isinstance(llvm_type, ir.ArrayType) and llvm_type.element == cls.char:
                # string
                str_val = parse_escape(const_value[1:-1]) + '\0'
                return ir.Constant(llvm_type, bytearray(str_val, 'ascii'))
            else:
                # TODO
                raise SemanticError(msg="No known conversion: '%s' to '%s'" % (const_value, llvm_type))
        else:
            raise SyntaxError(ctx=ctx, msg="get_const_from_str doesn't support const_value which is a " + str(type(const_value)))

    @classmethod
    def is_int(cls, type):
        """判断某个类型是否为整数类型"""
        return type in [cls.int, cls.short, cls.char]

    @classmethod
    def is_float(cls, type):
        """判断某个类型是否为浮点数类型"""
        return type in [cls.float, cls.double]

    @classmethod
    def cast_type(cls, builder, target_type, value, ctx):
        """
        强制类型转换
        :param builder:
        :param target_type:目标类型
        :param value:
        :return:转换后的数字
        """
        if value.type == target_type:  #如果转换前后类型相同，
            return value  #则不转换，直接返回

        if cls.is_int(value.type) or value.type == cls.bool:  #从整数或者布尔值
            if cls.is_int(target_type): #转成整数
                if value.type.width < target_type.width:  # 扩展整数位数
                    return builder.sext(value, target_type)
                else:  # 减少整数位数
                    return builder.trunc(value, target_type)
            elif cls.is_float(target_type):  #转成浮点数
                return builder.sitofp(value, target_type)
            elif target_type == cls.bool:
                return builder.icmp_unsigned('!=', value, cls.bool(0))

        elif cls.is_float(value.type):  #从浮点数
            if cls.is_float(target_type):  #转成浮点数
                if value.type == cls.float:  # 增加浮点数精度
                    return builder.fpext(value, target_type)
                else:  # 降低浮点数精度
                    return builder.fptrunc(value, target_type)
            elif cls.is_int(target_type):  #转成整数
                return builder.fptosi(value, target_type)

        elif type(value.type) == ir.ArrayType and type(target_type) == ir.PointerType \
                and value.type.element == target_type.pointee:  #数组类型转成指针类型
            zero = ir.Constant(cls.int, 0)
            tmp = builder.alloca(value.type)
            builder.store(value, tmp)
            return builder.gep(tmp, [zero, zero])
        elif isinstance(value.type, ir.ArrayType) and isinstance(target_type, ir.ArrayType) \
                and value.type.element == target_type.element:
            return builder.bitcast(value, target_type)
        raise SemanticError(ctx=ctx, msg="No known conversion from '%s' to '%s'" % (value.type, target_type))
