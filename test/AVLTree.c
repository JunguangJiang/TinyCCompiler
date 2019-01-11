int nullptr = 0;
int LH = 0;
int EH = 1;
int RH = 2;
int printf(const char *format,...);

struct AVLNode
{
	int m_data;
	int bf; // balance factor
	struct AVLNode* lchild;
	struct AVLNode* rchild;
};

struct AVLNode node_set[100];
int node_used[100];

void Init()
{
    for(int i = 0; i < 100; i++)
    {
        node_set[i].m_data = 0;
        node_set[i].bf = EH;
        node_set[i].lchild = nullptr;
        node_set[i].rchild = nullptr;
        node_used[i] = 0;
    }
}

struct AVLNode* AllocNode(int e)
{
    struct AVLNode* res = nullptr;
    for(int i = 0; i < 100; i++)
    {
        if(node_used[i] == 0)
        {
            node_used[i] = 1;
            node_set[i].m_data = e;
            node_set[i].bf = EH;
            node_set[i].lchild = nullptr;
            node_set[i].rchild = nullptr;
            res = &node_set[i];
            break;
        }
    }
    return res;
}

void R_Rotate(struct AVLNode ** p)
{
	struct AVLNode* q = (*p)->lchild;
	(*p)->lchild = q->rchild;
	q->rchild = *p;
	*p = q;
}

void L_Rotate(struct AVLNode ** p)
{
	struct AVLNode* q = (*p)->rchild;
	(*p)->rchild = q->lchild;
	q->lchild = *p;
	*p = q;
}

void Adjust(struct AVLNode ** root, int Type)
{
	struct AVLNode* p;
	switch (Type)
	{
	case LH:
		p = (*root)->lchild;
		if (p->bf == LH)
		{
			p->bf = EH;
			(*root)->bf = EH;
			R_Rotate(root);
		}
		else if (p->bf == RH)
		{
			struct AVLNode* q = p->rchild;
			switch (q->bf)
			{
			case LH:
				p->bf = EH;
				(*root)->bf = RH;
				break;
			case EH:
				p->bf = EH;
				(*root)->bf = EH;
				break;
			case RH:
				p->bf = LH;
				(*root)->bf = EH;
				break;
			}
			q->bf = EH;
			L_Rotate(&((*root)->lchild));
			R_Rotate(root);
		}
		break;
	case RH:
		p = (*root)->rchild;
		if (p->bf == RH)
		{
			(*root)->bf = EH;
			p->bf = EH;
			L_Rotate(root);
		}
		else if (p->bf == LH)
		{
			struct AVLNode* q = p->lchild;
			switch (q->bf)
			{
			case LH:
				p->bf = RH;
				(*root)->bf = EH;
				break;
			case EH:
				p->bf = EH;
				(*root)->bf = EH;
				break;
			case RH:
				p->bf = EH;
				(*root)->bf = LH;
				break;
			}
			q->bf = EH;
			R_Rotate(&((*root)->rchild));
			L_Rotate(root);
		}
		break;
	}
}

int Insert(struct AVLNode ** root, int e, int* taller)
{
	if (*root == nullptr)
	{
		*root = AllocNode(e);
		*taller = 1;
	}
	else
	{
		if ((*root)->m_data == e)
		{
			*taller = 0;
			return 0;
		}
		if (!((*root)->m_data < e))
		{
			if (!Insert(&((*root)->lchild), e, taller))
				return 0;
			if (*taller)
			{
				switch ((*root)->bf)
				{
				case LH:
					Adjust(root, LH);
					*taller = 0;
					break;
				case EH:
					(*root)->bf = LH;
					*taller = 1;
					break;
				case RH:
					(*root)->bf = EH;
					*taller = 0;
					break;
				}
			}
		}
		else
		{
			if (!Insert(&((*root)->rchild), e, taller))
				return 0;
			if (*taller)
			{
				switch ((*root)->bf)
				{
				case LH:
					(*root)->bf = EH;
					*taller = 0;
					break;
				case EH:
					(*root)->bf = RH;
					*taller = 1;
					break;
				case RH:
					Adjust(root, RH);
					*taller = 0;
					break;
				}
			}
		}
	}
	return 1;
}

struct AVLNode* Search(struct AVLNode* p, int e)
{
    struct AVLNode* res;
	if (p == nullptr)
		res = p;
	else if (p->m_data == e)
		res = p;
	else if (p->m_data < e)
		res = Search(p->rchild, e);
	else
		res = Search(p->lchild, e);
    return res;
}

void PrintTree(struct AVLNode* root)
{
    if(root == nullptr)
    {
        printf("Empty Tree!\n");
        return;
    }
    printf("{");
    printf(" data: %d, ", root->m_data);
    printf(" lchild: ");
    if(root->lchild != nullptr)
        PrintTree(root->lchild);
    else
        printf("null");
    printf(", ");
    printf(" rchild: ");
    if(root->rchild != nullptr)
        PrintTree(root->rchild);
    else
        printf("null");
    printf("}");
}

int main()
{
    Init();
    struct AVLNode* root = AllocNode(0);
    int taller;

    PrintTree(root);
    printf("\n");

    Insert(&root, 1, &taller);
    PrintTree(root);
    printf("\n");

    Insert(&root, 2, &taller);
    PrintTree(root);
    printf("\n");

    Insert(&root, 4, &taller);
    PrintTree(root);
    printf("\n");

    Insert(&root, -22, &taller);
    PrintTree(root);
    printf("\n");

    Insert(&root, -25, &taller);
    PrintTree(root);
    printf("\n");
    return 0;
}