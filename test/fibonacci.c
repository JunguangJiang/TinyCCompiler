int scanf(const char * restrict format,...);
int printf(const char *format,...);

int fib(int n){
    if(n <= 0){
        return 0;
    }else if(n==1){
        return 1;
    }
    return fib(n-1) + fib(n-2);
}

int main()
{
    printf("Please input number n:");
    int n;
    scanf("%d", &n);
    printf("fib(n)=%d\n", fib(n));
    return 0;
}