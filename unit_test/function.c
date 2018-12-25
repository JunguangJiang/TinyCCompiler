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



int main()
{
    func1();
    func2(3);
    func3("Hello");
    func4(4.5,'a');
    int array[8] = {3,4,5,6,7,8,9,10};
    func5(array, 8);
    return 0;
}
