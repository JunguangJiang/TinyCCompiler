//四则运算测试程序
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>

///运算符优先等级[栈顶][当前]
char pri[7][7]={
    /*			当前运算符					*/
    /*			+	-	*	/	(	)	\0	*/
    /*   +  */	'>','>','<','<','<','>','>',
    /*栈 -  */	'>','>','<','<','<','>','>',
    /*顶 *  */	'>','>','>','>','<','>','>',
    /*运 /  */	'>','>','>','>','<','>','>',
    /*算 (  */	'<','<','<','<','<','=',' ',
    /*符 )  */	' ',' ',' ',' ',' ',' ',' ',
    /*   \0 */	'<','<','<','<','<',' ','='
};

///运算符和编号之间的对应关系
//进一步改进：改成switch语句
int optr2rank(char op)
{
	if (op == '+'){
		return 0;
	} else if (op == '-'){
		return 1;
	} else if (op == '*'){
		return 2;
	} else if (op == '/'){
		return 3;
	} else if (op == '('){
		return 4;
	} else if (op == ')'){
		return 5;
	} else if (op == '\0'){
		return 6;
	} else {
		exit(-1);
	}
}

///比较两个运算符之间的优先级
char orderBetween(char op1, char op2)
{
	return pri[optr2rank(op1)][optr2rank(op2)];
}

///计算opnd1 op opnd2的结果
///opnd1: 操作数1
///op: 运算符
///opnd2: 操作数2
int calcu(int opnd1, char op, int opnd2)
{
	if (op == '+') {
		return opnd1 + opnd2;
	} else if (op == '-') {
		return opnd1 - opnd2;
	} else if (op == '*') {
		return opnd1 * opnd2;
	} else if (op == '/') {
		return opnd1 / opnd2;
	} else {
		exit(-2);
	}
}

///对表达式求值
///assert:表达式必须是合法的四则运算表达式，对于非法的表达式没有异常处理
//为方便编译程序的编写，暂时按照整数类型进行计算
//后续可以改成返回float的结果
int evaluate(char S[])
{
	int opnd[10000]; //运算数栈
	int opnd_top = -1; //运算数栈顶
	char optr[10000]; //运算符栈
	int optr_top = -1; //运算符栈顶

	int i=0; //当前正在扫描字符串S中的位置

	optr[++optr_top] = '\0'; //尾哨兵'\0'也作为头哨兵首先入栈
	while (optr_top >= 0) { //在运算符栈非空之前，逐个处理表达式中各字符
		if (isdigit(S[i])) { //若当前字符为操作数，则将起始于S[i]的子串解析为数值，并存入操作数栈
			opnd[++opnd_top] = S[i] - '0'; //Note:转成float时，此处需要修改!
			while(isdigit(S[++i])){
				opnd[opnd_top] = opnd[opnd_top] * 10 + S[i] - '0';
			}
		} else { //若当前字符为运算符，则
			char order = orderBetween(optr[optr_top], S[i]); //视其与栈顶运算符之间的优先级高低分别处理
			if (order == '<') { //栈顶运算符优先级更低时，
				optr[++optr_top] = S[i++]; //计算推迟，当前运算符进栈
			} else if (order == '=') { //优先级相等（当前运算符为右括号或者尾部哨兵'\0'时，
				optr_top--; //脱括号
				i++; //接收下一个字符
			} else if (order == '>') { //栈顶运算符优先级更高时，可实施相应的计算，并将结果重新入栈
				char op = optr[optr_top--];
				int pOpnd2 = opnd[opnd_top--], pOpnd1 = opnd[opnd_top--]; //取出后、前操作数
				opnd[++opnd_top] = calcu(pOpnd1, op, pOpnd2);
			} else { //逢语法错误，不做处理直接退出
				exit(-1);
			}
		}
	}
	return opnd[opnd_top]; //返回最终的计算结果
}

void testEvaluate(char S[], int true_answer)
{
	int test_answer = evaluate(S);
	if(test_answer == true_answer){
		printf("pass:");
	}else{
		printf("fail:");
	}
	printf("'%s' = %d", S, test_answer);
	if(test_answer != true_answer){
		printf(", while true answer is %d", true_answer);
	}
	printf("\n");
}

void evaluateTests()
{
	printf("四则运算测试:\n");
	testEvaluate("3", 3);
	testEvaluate("23+5", 28);
	testEvaluate("3*4", 12);
	testEvaluate("22-(6-4)", 20);
	testEvaluate("22/(6/3)",11);
	testEvaluate("1+(5-2)*4/(2+1)", 5);
	testEvaluate("0+(1+23)/4*5*67-8+9", 2011);
	testEvaluate("192/(3*8+4*(33/5))-5", -1);
	printf("\n");
}

int main()
{
	evaluateTests();
}
