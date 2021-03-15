# Rax

## 클러스터의 이야기를 먼저 한다.
- 클러스터와 standalone의 차이는?
  - 클러스터를 구성하는 마스터 노드 간의 데이터 분배를 위한 슬롯이 있음
    - CRC16(key) % 16384
  - 마스터 노드는 자신이 보유한 슬롯에 대해서만 요청을 처리한다.
  - 슬롯의 이동
    - 클러스터를 온라인으로 확장하기 위해서 슬롯을 이동시킬 수 있다.
      - MOVED
      - ASK
    - 보유하고 있는 키 중에서, 특정 슬롯의 키를 옮겨야 한다
      - 단순히 해시로 가능하지 않을까? 리스트로?
        - 문자열 비교 및 중복 체크?
        - 저장 공간의 한계?

### 버전 3에서는?
- SortedSet을 이용
  - Sorted(정렬된) + Set (집합, 중복이 없는!)
  - Time Complexity: `O(log(N))`
    - 속도가 그렇게 좋지는 못한..

### 버전 4부터 rax가 도입
- 빠른 탐색 속도
  - O(n): n은 문자열의 길이
- 저장 공간의 절약
  - 접미사를 공통으로 사용
  - 동일한 노드는 압축으로 표현
- 클러스터의 슬롯만을 타겟으로 하지 않는다.
  - 5버전부터는 스트림에서도 사용되며, 향후 확대될 가능성이 높음
    - in stream
      - rax + listpack
        - 우리는 listpack에 대해서도 공부해야합니다..

## Rax를 알아보자
### 먼저 Trie부터!
- 참고
  - https://en.wikipedia.org/wiki/Trie
  - https://zhu45.org/posts/2018/Jun/02/trie/
- 문자열을 빠르게 검색하기 위한 방법
- 개별 노드는 하나의 문자를 포함하며, 다음 문자를 가리키는 포인터를 가진다.
- 각각의 노드에는 char에 대한 배열을 가지며, 문자열의 코드로 직접 배열에 접근하여 값을 가져온다.
  - ascii/ansi/unicode/utf8 참고할 것
- 저장 효율이 좋지 않다.
  - 모든 문자에 대해 개별적인 노드가 필요할 것이며,
  - 각각의 노드가 큰 배열을 가져야한다.

## Radix Tree
- 접미사를 압축해서 저장한다.
  - prefix trie라고도 불리는 듯 하다.
- rax는 radix tree를 redis에 맞게 구현한 것

## Rax
- 대체로 동일한 속성을 가진다.
  - 마지막 키를 나타내는 노드에는 데이터도 저장할 수 있다!
  - 이러한 이유로 Hash등을 대체할 수도 있다.


## 다시 돌아와서 클러스터에서는?
- 문자열의 앞에 2바이트를 새로 밀어넣고, 해시 슬롯의 정보를 담는다.
- 즉, 해시 슬롯의 정보가 문자열의 prefix와 같은 역할을 한다.

## 스트림에서는?
- 

# Iterator

## raxStack
```c++
#define RAX_STACK_STATIC_ITEMS 32
typedef struct raxStack {
    void **stack; /* Points to static_items or an heap allocated array. */
    size_t items, maxitems; /* Number of items contained and total space. */
    /* Up to RAXSTACK_STACK_ITEMS items we avoid to allocate on the heap
     * and use this static array of pointers instead. */
    void *static_items[RAX_STACK_STATIC_ITEMS];
    int oom; /* True if pushing into this stack failed for OOM at some point. */
} raxStack;
```
- `raxLowWalk()`를 위한 자료구조
- 부모의 리스트를 호출한 곳(caller)에게 전달한다
- 각 노드는 부모관련 필드가 없다. (메모리 관련 우려)

## raxStart
```c++
void raxStart(raxIterator *it, rax *rt);
```
- `raxIterator`를 초기화한다.

## raxSeek
```c++
int raxSeek(raxIterator *it, const char *op, unsigned char *ele, size_t len);
```
- 지정된 엘리먼트에서 반복할 곳을 찾는다.
- 1이 반환되면 성공, 0을 반환하면 실패한 것 (oom 또는 기타)

## raxLowWalk
```c++
static inline size_t raxLowWalk(rax *rax, unsigned char *s, size_t len, raxNode **stopnode, raxNode ***plink, int *splitpos, raxStack *ts);
```
- 특정 길이(len)의 문자열(s)를 찾기 위한 저수준(low level)의 함수
- 키의 문자 수를 반환
    - 반환되는 수가 len과 같으면, 관련이 있는 노드를 찾았다는 의미
    - 하지만, 이 문자열은 node->iskey가 0이면 키가 아니거나,
    - 압축된 노드의 중간에 멈춘다면, splitpos는 0이 아니게 된다.
- len과 같이 않은 수가 반환되는 경우, 문자열이 일치하지 않았다.


## raxNext or raxPrev
```c++
/* Go to the next element in the scope of the iterator 'it'.
 * If EOF (or out of memory) is reached, 0 is returned, otherwise 1 is
 * returned. In case 0 is returned because of OOM, errno is set to ENOMEM. */
int raxNext(raxIterator *it);

/* Go to the previous element in the scope of the iterator 'it'.
 * If EOF (or out of memory) is reached, 0 is returned, otherwise 1 is
 * returned. In case 0 is returned because of OOM, errno is set to ENOMEM. */
int raxPrev(raxIterator *it);
```

