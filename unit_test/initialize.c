int printf(const char *format,...);

// Test
int main()
{
    float i=5.5666;
    printf("i=%f\n", i);
    double i2 = 4.444;
    printf("i2=%f\n",i2);
    char j = 4;
    printf("j=%d\n", j);
    int k = 5;
    printf("k=%d\n", k);
    char s[5] = "5\t6\n";
    s[2] = 33;
    printf("%s", s);
    return 0;
}