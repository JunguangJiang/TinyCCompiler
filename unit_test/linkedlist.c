struct Node
{
    int num;
    double price;
    int *ip;
    struct Node* next;
}n,*np;
int main()
{
    struct Node n2;
    n.num = 1;
    int *a=&(n.num);
    printf("-------------------\n");
    printf("%d\n", ++n.num);
    printf("%d\n", ++(*a));
    printf("%d\n", n.num);
    n2.num=n.num*n.num;
    printf("%d\n", n2.num);
    struct Node* n3;
    n3=&n2;
    printf("%d\n", n3->num);
    int aa=2;
    n3->ip = &aa;
    printf("%d\n", *n2.ip);
    n.next = &n2;
    printf("%d\n", n.next->num);
    //printf("%d\n", n2.num);
    //Node n1;
    //n1.num = 11;
    //n1.price = 5.2;
    //Node* np = &n1;
    //printf("%d\n", np->num);
    //printf("%d\n", np->price);
    return 0;
}