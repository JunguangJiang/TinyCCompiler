//#include <string.h>
//#include <stdio.h>
//#include <stdlib.h>
//#include <ctype.h>
int printf(const char *format,...);
void exit(int status);

char pri[7][7]={
    /*			+	-	*	/	(	)	\0	*/
    /*  +  */	{'>','>','<','<','<','>','>'},
    /* -  */	{'>','>','<','<','<','>','>'},
    /* *  */	{'>','>','>','>','<','>','>'},
    /* /  */	{'>','>','>','>','<','>','>'},
    /* (  */	{'<','<','<','<','<','=',' '},
    /* )  */	{' ',' ',' ',' ',' ',' ',' '},
    /*  \0 */	{'<','<','<','<','<',' ','='}
};

int optr2rank(char op)
{
    int ans = 0;
	if (op == '+'){
		ans = 0;
	} else if (op == '-'){
		ans = 1;
	} else if (op == '*'){
		ans = 2;
	} else if (op == '/'){
		ans = 3;
	} else if (op == '('){
		ans = 4;
	} else if (op == ')'){
		ans = 5;
	} else if (op == '\0'){
		ans = 6;
	} else {
	    printf("optr2rank error: %c", op);
		exit(-1);
	}
	return ans;
}

char orderBetween(char op1, char op2)
{
	return pri[optr2rank(op1)][optr2rank(op2)];
}

int calcu(int opnd1, char op, int opnd2)
{
    int ans = 0;
	if (op == '+') {
		ans = opnd1 + opnd2;
	} else if (op == '-') {
		ans = opnd1 - opnd2;
	} else if (op == '*') {
		ans = opnd1 * opnd2;
	} else if (op == '/') {
		ans = opnd1 / opnd2;
	} else {
		exit(-2);
	}
	return ans;
}

bool isdigit(char c){
    int i = c - '0';
    return (i >= 0) && (i <= 9);
}

int evaluate(char S[])
{
	int opnd[10000];
	int opnd_top = -1;
	char optr[10000];
	int optr_top = -1;

	int i=0;

	optr[++optr_top] = '\0';

	while (optr_top >= 0) {
		if (isdigit(S[i])) {
			opnd[++opnd_top] = S[i] - '0';
			while(isdigit(S[++i])){
				opnd[opnd_top] = opnd[opnd_top] * 10 + S[i] - '0';
			}
		} else {
			char order = orderBetween(optr[optr_top], S[i]);
			if (order == '<') {
				optr[++optr_top] = S[i++];
			} else if (order == '=') {
				optr_top--;
				i++;
			} else if (order == '>') {
				char op = optr[optr_top--];
				int pOpnd2 = opnd[opnd_top--], pOpnd1 = opnd[opnd_top--];
				opnd[++opnd_top] = calcu(pOpnd1, op, pOpnd2);
			} else {
				exit(-1);
			}
		}
	}
	return opnd[opnd_top];
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
	printf("evaluateTests:\n");
	testEvaluate("3", 3);
	testEvaluate("23+5", 28);
	testEvaluate("3*4", 12);
	testEvaluate("22-(6-4)", 20);
	testEvaluate("22/(6/3)",11);
	testEvaluate("1+(5-2)*4/(2+1)", 5);
	testEvaluate("0+(1+23)/4*5*67-8+9", 2011);
	testEvaluate("192/(3*8+4*(33/5))-5", -1);
}

int main()
{
	evaluateTests();
    return 0;
}
