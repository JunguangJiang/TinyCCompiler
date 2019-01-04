#include <stdio.h>

int test_switch(int a) {
	int b;
	switch (a) {
	case 1:
		b = 1;
	case 2:
		b = 2;
		break;
	case 3:
	case 4:
		b = 4;
		break;
	case 5:
		b = 5;
		break;
	default:
		b = 6;
		break;
	}
	return b;
}

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
	printf("=====Start test switch=====\n");
	printf("should be %d\n", test_switch(1));
	printf("should be %d\n", test_switch(2));
	printf("should be %d\n", test_switch(3));
	printf("should be %d\n", test_switch(4));
	printf("should be %d\n", test_switch(5));
	printf("should be %d\n\n", test_switch(6));
	return 0;
}