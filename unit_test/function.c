int printf(const char *format,...);

int abs(int x);

// test visitFunctionDefinition
int func1()
{
    printf("func1 called.\n");
    return 1;
}

void func2(short i)
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

void func5(int array[], int n)
{
    printf("func5 called with array=[");
    for(int i=0;i<n;i++){
        printf("%d,", array[i]);
    }
    printf("] and n=%d\n",n);
}

void inner_func(int i)
{
    printf("inner function called with i=%d\n", i);
    if(i>0){
        inner_func(i/8);
    }
}

void outter_func(int j)
{
    printf("outter function called with j=%d\n", j);
    inner_func(j*j);
}

int func_declaration(int i, int j);

void extern_func_declaration_test()
{
    printf("extern function decalaration test:");
    printf("abs(-4)=%d\n", abs(-4));
}

int main()
{
    func1();
    func2(3);
    func3("Hello");
    func4(4.5,'a');
    int array[8] = {3,4,5,6,7,8,9,10};
    func5(array, 8);
    outter_func(8);
    printf("function decalaration: 3*5=%d\n", func_declaration(3,5));
    extern_func_declaration_test();
    return 0;
}

int func_declaration(int i, int j)
{
    return i*j;
}