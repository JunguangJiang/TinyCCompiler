// test visitFunctionDefinition
int func1()
{
    printf("func1 called.\n");
    return 1;
}

void func2(int i)
{
    printf("func2 called with i=%d.\n", i);
}

void func3(char s[])
{
    printf("func3 called with s=%s.\n", s);
}

float func4(float i, char c)
{
    printf("func4 called with i=%3.2f and c=%c\n", i, c);
    return i;
}

int main()
{
    func1();
    func2(3);
    func3("Hello");
    func4(4.5,'a');
    return 0;
}
