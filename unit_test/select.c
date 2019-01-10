int switch_func(int a) {
	int b;
	switch (a) {
	case 1:
		b = 1;
	case 2:
		b = 2;
		break;
	case 3:
	case 4:
		b = 4;
		break;
	case 5:
		b = 5;
		break;
	default:
		b = 6;
		break;
	}
	return b;
}

void switch_test_1()
{
    printf("switch test 1:");
    for(int i=1; i<=6; i++){
        printf("%d,", switch_func(i));
    }
    printf("\n");
}

int if_func(int a)
{
    int b=0;
    if(a==1){
        b=1;
    }else if(a==2){
        b=2;
    }else{
        if(a>=3){
            b=3;
            if(a==4){
                b=4;
            }else{
                b=5;
            }
        }
    }
    return b;
}

void if_test_1()
{
    printf("if test 1:");
    for(int a=0; a<5; a++){
        printf("%d,", if_func(a));
    }
    printf("\n");
}


int main()
{
    switch_test_1();
    if_test_1();
    return 0;
}