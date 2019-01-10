int nullptr = 0;
struct Node
{
    int data;
    struct Node* next;
};
void addNode(struct Node* pre, struct Node* next)
{
    pre->next = next;
}
int main()
{
    struct Node n1, n2, n3;
    n1.data = 1;
    n1.next = nullptr;
    n2.data = 2;
    n2.next = nullptr;
    n3.data = 3;
    n3.next = nullptr;
    addNode(&n1, &n2);
    addNode(&n2, &n3);

    Node* head = n1;
    Node* cur = head;
    do
    {
        cur = cur->next;
        printf("data=%d\n", cur->data);
    }while(cur!=nullptr);
    return 0;
}