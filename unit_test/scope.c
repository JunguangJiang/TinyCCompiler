int i=0;
void scope_test_1()
{
    printf("scope test 1:\n");
    printf("global i=%d\n", i);
    int i = 1;
    printf("inner 1 i=%d\n",i);
    if(1){
        int i=2;
        printf("inner 2 i=%d\n",i);
        while(1){
            int i=3;
            printf("inner 3 i=%d\n",i);
            if(1){
                break;
            }
        }
        printf("inner 2 i=%d\n",i);
    }
    printf("inner 1 i=%d\n",i);
}


int main()
{
    scope_test_1();
    printf("global i=%d\n", i);
    return 0;
}