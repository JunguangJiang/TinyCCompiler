int printf(const char *format,...);

void array_test_1()
{
    int array[3][4] = {
        {1,2,3,4},
        {5,6,7,8},
        {9,11,12,13}
    };
    printf("array=\n");
    for(int i=0; i<3; i++)
    {
        for(int j=0; j<4; j++){
            printf("%d,", array[i][j]);
        }
        printf("\n");
    }
}

void char_array_test()
{
    char c=33;
    printf("%c\n", c);
    char* s = "Hello world";
    printf("%s\n", s);
}
int main()
{
    array_test_1();
    char_array_test();
    return 0;
}