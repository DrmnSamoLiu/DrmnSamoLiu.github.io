
//Author : DuSu
//gcc key.c -o key && ./key
//KEY: 5982a0a3

#include <stdio.h>

unsigned int hash(char *str) {
	char bVar1;
	char cVar2;
	unsigned int uVar3;
	unsigned int uVar4;
	
	if (str == (char *)0x0) {
		puts("str is null ptr");
		uVar3 = 0;
	}
	else {
		str = str + 1;
		uVar3 = 0;
		uVar4 = 0;
		do {
			cVar2 = str[-1];
			if (cVar2 == '\0') {
				return uVar3;
			}
			if (0xb < uVar4) {
				return uVar3;
			}
			if (cVar2 != '\"') {
				uVar4 = uVar4 + 1;
				uVar3 = ((int)cVar2 + uVar3 * 0x1f) % 0x7fffffff;
			}
			bVar1 = (str != (char *)0x0);
			str = str + 1;
		} while (bVar1);
	}
	return uVar3;
}

int main(int argc, char *argv[]) {
	char buf[0xc] = "C200 1.0";
	unsigned int key = hash(buf);
	printf("KEY: %08x\n", key);
}
