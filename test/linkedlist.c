struct Node
{
    int num;
    double price;
};
int main()
{
    Node n1;
    n1.num = 11;
    n1.price = 5.2;
    Node* np = &n1;
    printf("%d\n", np->num);
    printf("%d\n", np->price);
    return 0;
}