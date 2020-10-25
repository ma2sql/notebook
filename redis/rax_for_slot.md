# 클러스터의 슬롯을 관리하기 위해서 만들어진 rax

- 키를 `slots_to_keys`(rax)에 저장할 때, 키 앞의 2바이트를 해시 슬롯 번호를 저장하는데 사용한다.
- 즉, 해시 번호가 rax를 구성하는 문자열에서 prefix와 같은 역할을 한다.
- 만약, key가 `foo` 라면?
  - 키의 해시 슬롯 번호를 구한다.
  - 해시 슬롯 번호를 비트 연산을 통해서, 1바이트씩 문자로 변환한다.
  - 그렇게 만들어진 2개의 문자를 키의 맨 앞으로 붙인다.
```c
unsigned int hashslot = keyHashSlot(key,keylen);
...
indexed[0] = (hashslot >> 8) & 0xff;
indexed[1] = hashslot & 0xff;
...
memcpy(indexed+2,key,keylen)
```