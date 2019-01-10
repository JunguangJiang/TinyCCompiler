struct Node
{
    int data;
    Node* next;
};
void addNode(Node* pre, Node* next)
{
    pre->next = next;
}
int main()
{
    Node n1, n2, n3;
    n1.data = 1;
    n1.next = 0;
    n2.data = 2;
    n2.next = 0;
    n3.data = 3;
    n3.next = 0;
    addNode(&n1, &n2);
    addNode(&n2, &n3);

    Node* head = n1;
    Node* cur = head;
    do
    {
        cur = cur->next;
        printf("data=%d\n", cur->data);
    }while(cur!=0);
    return 0;
}