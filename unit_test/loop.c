int printf(const char *format,...);

void for_test_1()
{
    int data[6]={4,5,6,7,8,9};
    int sum = 0;
    for(int i=0; i<6; i++){
        sum += data[i];
    }
    printf("for test 1: sum=%d\n",sum);
}

void for_test_2()
{
    printf("for test 2:");
    for(int m=100; m<=200; m=m+3){
        printf("%d,", m);
        if((m%11)==0){
            printf("break!");
            break;
        }
    }
    printf("\n");
}

void for_test_3()
{
    for(int i=0, j=1; i<3; i++){
        j *= 3;
        if(i==2){
            printf("j=%d\n",j);
            break;
        }
    }
}

void while_test_1()
{
    printf("while test 1:");
    short i = 1;
    while(i<30){
        printf("%d,", i);
        i *= 3;
    }
    printf("\n");
}

void while_test_2()
{
    printf("while test 2:");
    int result = 1;
    int i = 0;
    while(i<20){
        i++;
        if((i%3)==0){
            continue;
        }else if(i>10){
            break;
        }else{
            result *= i;
        }
    }
    printf("result=%d\n", result);
}

void triple_break()
{
    int i=0,j=0,k=0;
    while(1){
        i++;
        while(1){
            j++;
            while(1){
                k++;
                if(k>3){
                    printf("k break,");
                    break;
                }
            }
            if(j>3){
                printf("j break,");
                break;
            }
        }
        if(i>3){
            printf("i break");
            break;
        }
    }
}

int main()
{
    for_test_1();
    for_test_2();
    for_test_3();
    while_test_1();
    while_test_2();
    triple_break();
    return 0;
}
