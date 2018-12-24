//回文检测
#include <string.h>
#include <stdio.h>

int strlen(char s[])
{
    int i=0;
    while(s[i]) i++;
    return i;
}

////判断字符串s是否是回文串
int isPalindrome(char s[])
{
    int len = strlen(s);
    for(int i=0, mi=len/2; i<mi; i++){
        if(s[i] != s[len-1-i]){
            return 0;
        }
    }
    return 1;
}

void testPalindrome(char s[], int true_answer)
{
    int test_answer = isPalindrome(s);
    if(test_answer == true_answer){
        printf("pass:");
    }else{
        printf("fail:");
    }
    printf("'%s' is ", s);
    if(test_answer == 0){
        printf("not ");
    }
    printf("a palindrome.\n");
}

void palindromeTests()
{
    printf("palindromeTests:\n");
    testPalindrome("", 1);
    testPalindrome("1", 1);
    testPalindrome("22", 1);
    testPalindrome("23", 0);
    testPalindrome("234565432", 1);
    testPalindrome("234566432", 0);
    testPalindrome("3344", 0);
    testPalindrome("234", 0);
}

int main()
{
    palindromeTests();
}