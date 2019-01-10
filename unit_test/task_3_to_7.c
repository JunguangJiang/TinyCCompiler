#include <stdio.h>

void test_assignment() {
	int a;
	printf("=====Start test assignment=====\n");
	a = 1;
	printf("a = %d\n", a);
	a = a + 1;
	printf("a = a + 1, a = %d\n", a);
	a = a - 1;
	printf("a = a - 1, a = %d\n", a);
	a = a * 2;
	printf("a = a * 2, a = %d\n", a);
	a = a / 2;
	printf("a = a / 2, a = %d\n", a);
	a = 7;
	a = a % 4;
	printf("a = 7, a %%= 4, a = %d\n", a);
	a = a << 1; // 6
	printf("a = a << 1, a = %d\n", a);
	a = a >> 1; // 3
	printf("a = a >> 3, a = %d\n", a);
	a = a & 5; // 1
	printf("a = a & 3, a = %d\n", a);
	a = a | 4; // 5
	printf("a = a | 3, a = %d\n", a);
	a = a ^ 3; // 6
	printf("a = a ^ 3, a = %d\n\n", a);
}

void test_operator() {
	int a;
	printf("=====Start test operator=====\n");
	a = 1;
	printf("a = %d\n", a);
	a += 1;
	printf("a += 1, a = %d\n", a);
	a -= 1;
	printf("a -= 1, a = %d\n", a);
	a *= 2;
	printf("a *= 2, a = %d\n", a);
	a /= 2;
	printf("a /= 2, a = %d\n", a);
	a = 7;
	a %= 4;
	printf("a = 7, a %%= 4, a = %d\n", a);
	a <<= 1; // 6
	printf("a <<= 1, a = %d\n", a);
	a >>= 1; // 3
	printf("a >>= 1, a = %d\n", a);
	a &= 5; // 1
	printf("a &= 5, a = %d\n", a);
	a |= 4; // 5
	printf("a |= 4, a = %d\n", a);
	a ^= 3; // 6
	printf("a ^= 3, a = %d\n\n", a);
}

void test_conditional() {
	printf("=====Start test conditional=====\n");
	printf("(2 < 3 ? 2 : 3) is %d\n", 2 < 3 ? 2 : 3);
	printf("(2 > 3 ? 2 : 3) is %d\n\n", 2 > 3 ? 2 : 3);
}

void test_logical_and_or() {
	int a = 0;
	char t[] = "true";
	char f[] = "false";
	printf("=====Start test logical and or=====\n");
	printf("a = %d\n", a);
	printf("(2 < 3 && (a += 1)) is %s\n", (2 > 3 && (a += 1)) ? t : f);
	printf("and now a = %d\n", a);
	printf("((a += 1) && (3 > 2 || (a += 1))) is %s\n", ((a += 1) && (3 > 2 || (a += 1))) ? t : f);
	printf("and now a = %d\n\n", a);
}

int main() {
	test_operator();
	test_conditional();
	test_assignment();
	test_logical_and_or();
	return 0;
}