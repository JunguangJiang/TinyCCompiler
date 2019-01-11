#include <stdio.h>
int main(){
    int a = 4;
    while(a++<7)
        printf("%d\n", a);
    do{
        printf("%d\n", a);
        a--;
    }while(a>2);
    int b=8;
    printf("b=%d\n", b);
    printf("!b=%d\n", !b);
    printf("!!b=%d\n", !!b);
    printf("!!!b=%d\n", !!!b);
    printf("!!!!b=%d\n", !!!!b);
    printf("~b=%d\n", ~b);
    printf("~~b=%d\n", ~~b);
    return 0;
}