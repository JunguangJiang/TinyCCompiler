int printf(const char *format,...);
void *malloc(unsigned int num_bytes);
void free(void *ptr);

void mul(int* i_ptr, int *j_ptr)
{
    int k=(*i_ptr) * (*j_ptr);
    printf("i=%d, j=%d, i*j=%d\n",*(i_ptr),*(j_ptr),k);
}

void add(int *a, int i){
    (*a) = (*a) + i;
}

void swap(int *p1, int *p2)
{
    int tmp;
    tmp = *p1;
    *p1 = *p2;
    *p2 = tmp;
}

int main()
{
    //TEST 1
    int i=5;
    int j=6;
    mul(&i, &j);

    //TEST 2
    add(&i, 10);
    printf("i=%d\n",i);

    //TEST 3
    int d1=1,d2=3;
    swap(&d1, &d2);
    printf("d1=%d, d2=%d\n", d1, d2);

    //TEST 4
    int a[4] = {4,5,6,7};
    int *a_ptr = &a[1];
    printf("a[1]=%d\n", *a_ptr);

    //TEST 5
    swap(&a[1], &a[3]);
    printf("a[1]=%d, a[3]=%d\n", a[1], a[3]);

    //TEST 6
    swap(a, &a[2]);
    printf("a[0]=%d, a[2]=%d\n", a[0], a[2]);

    //TEST 7
    float f = 5.0;
    float* f_ptr = &f;
    *f_ptr = 7;
    printf("f=%f\n", f);

    //TEST 8
    int ** a_ptr_ptr = &a_ptr;
    printf("a[1] is %d\n", **a_ptr_ptr);

    //TEST 9
    double *malloc_ptr=0;
    malloc_ptr = malloc(8);
    *malloc_ptr = 3.0;
    printf("*malloc_ptr=%e\n", *malloc_ptr);
    free(malloc_ptr);

    //TEST 10
    struct my_struct{
        int i;
        double f;
    };
    struct my_struct* S=malloc(12);
    S->i=3;
    S->f=4.4;
    printf("S->i=%d,S->f=%e\n", S->i, S->f);
    free(S);
    
    return 0;
}
