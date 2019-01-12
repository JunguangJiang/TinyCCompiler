//KMP TEST
//#include <stdio.h>
int printf(const char *format,...);

int strlen(char s[])
{
    int i=0;
    while(s[i]) i++;
    return i;
}

int match(char s[], char t[], int pos, int next[])
{
	int i = pos;
	int j = 0;
	while ((i < strlen(s)) && (j < strlen(t)))
	{
		if ((j == -1) || s[i] == t[j])
		{
			i++;
			j++;
		}
		else
		{
			j = next[j];
		}
	}

	if (strlen(t) == j)
	{
		return i - strlen(t);
	}
    return -1;
}


void get_next(char t[], int next[])
{
	int k = -1;
	int j = 0;
	next[j] = k;
	while (j < strlen(t))
	{
		if ((k == -1) || (t[j] == t[k]))
		{
			++k;
			++j;
			next[j] = k;
		}
		else
		{
			k = next[k];
		}
	}
}


void print_next(int next[], int n)
{
	for (int i = 0; i < n; i++)
	{
		printf("next[%d] = %d\n", i, next[i]);
	}
}

int main()
{
	char s[] = "ababcabcacbab";
	char t[] = "abcac";
	int pos = 0;
	int index;
    int next[32];


	printf("\nKMP test:\n");
	get_next(t, next);
	print_next(next, strlen(t));

	index = match(s, t, pos, next);
	printf("index = %d\n", index);
	return 0;
}
