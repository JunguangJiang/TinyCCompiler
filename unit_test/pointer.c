
void mul(int* i_ptr, int *j_ptr)
{
    int k=(*i_ptr) * (*j_ptr);
    printf("i=%d, j=%d, i*j=%d\n",*(i_ptr),*(j_ptr),k);
}

void add(int *a, int i){
    (*a) = (*a) + 1;
}


int main()
{
    int i=5;
    int j=6;
//    mul(&i, &j);

    add(&i, 0);
    printf("i=%d\n",i);
    return 0;
}