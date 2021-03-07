주요 기능(Major features):

* 메모리 의식(Memory conscious):
    + 압축된 노드의 표현
    + 키가 NULL로 설정될 때, 노드 내에서는 NULL 포인터를 저장하지 않는다. (노드 헤더에 `isnull` 비트가 있다.)
    + 부모 노드 참조가 없다. 대신 필요할 때에는 스택이 사용된다.
* 빠른 검색(Fast lookups):
    + 엣지는 부모 노드에 바이트의 배열이 직접 저장되며, 매치되는 것을 찾으려고 하는 동안에 유용하지 않은 자식 노드에는 접근할 필요가 없다. 이것은 다른 구현과 비교해서 캐시 미스가 적다는 것을 의미한다.
    + 엣지를 2개의 분리된 배열로 저장함으로써, 올바른 자식 노드에 대한 라인 친화적인 스캐닝을 캐시한다. 그 중 하나는 엣지 문자들의 배열이고, 다른 하나는 엣지 포인터이다.
* 완전한 구현(Complete implementation):
    + 필요에 따라 노드를 재압축(re-compression)하는 삭제
    + (트리가 수정되는 동안 반복자를 사용하는 방법을 포함하는) 이터레이터(또는 반복자). 
    + Random walk iteration.
    + 무작위 보행의 반복 (Random walk iteration)
    + 메모리 부족(Out of memory)을 보고하고 억제하는 기능: 만약 `malloc()`이 NULL을 반환하면, API는 OOM 에러를 보고하고, 항상 트리를 일관된 상태로 유지한다.
* 읽기 쉽고, 유연한 구현(Readable and fixable implementation):
    + 모든 복잡한 부분들은 알고리즘의 상세와 함께 주석이 추가되어 있다.
    + 주어진 함수를 호출할 때 구현이 무엇을 하는지 이해하기 위해 디버깅 메시지는 활성화될 수 있다.
    + 기수 트리(radix tree) 노드의 표현을 ASCII 아트로 출력하는 기능이 있다.
* 이식 가능한 구현(Portable implementation):
    + 메모리에 대해 정렬되지 않은 접근은 절대 하지 않는다.
    + ANSI C99로 작성되었고, 확장(extensions)은 사용하지 않는다.
* Extensive code and possible states test coverage using fuzz testing.
* 퍼지 테스트를 이용한 광범위한 코드와 있을 수 있는 상태에 대한 테스트 커버리지 (Extensive code and possible states test coverage using fuzz testing)
    + 테스트는 일반적이지 않은 상태를 탐색하기 위한 퍼징에 많이 의존한다.
    + 단순한 해시 테이블과 정렬된 배열의 동일한 행동의 구현과 비교되는 딕셔너리와 반복자의 구현. 랜덤한 데이터를 생성하고 2개의 구현의 결과가 맞는지 체크한다.
    + 메모리 부족(out of memory) 조건에 대한 테스트. 이 구현은 무작위로 `NULL` 을 반환하는 특별한 할당자(allocator)로 퍼즈된다. 기수 트리(radix tree의) 결과는 일관성을 위해서 테스트된다. 이 구현의 주 타겟인 레디스(Redis)는 이 피쳐를 사용하지 않지만, OOM을 다루는 이 기능은 OOM으로부터 살아남아야하는 기능이 필요로 한 곳에서 이 구현이 유용할 수 있다.
    + 레디스에서: 이 구현은 현실 세계에서 매우 강조된다.

노드의 레이아웃은 다음과 같다. 이 예에서, 노드는 키를 표현하고 (그래서 연결되는 데이터 포인터가 있으며), `x`, `y`, `z`의 3개의 자식을 가진다. 다이어그램에서 모든 공간(space)는 바이트를 표현한다.

    +----+---+--------+--------+--------+--------+
    |HDR |xyz| x-ptr  | y-ptr  | z-ptr  |dataptr |
    +----+---+--------+--------+--------+--------+

The header `HDR` is actually a bitfield with the following fields:
헤더 `HDR`은 실제로 다음의 필드들을 가지는 비트 필드이다.

    uint32_t iskey:1;     /* 이 노드가 키를 포함하는가? */
    uint32_t isnull:1;    /* 연결된 값은 NULL이며, 저장되지 않는다 */
    uint32_t iscompr:1;   /* 노드는 압축된다 */
    uint32_t size:29;     /* 자식의 수 또는 압축된 문자열의 길이 */

압축된 노드들은 키가 아니며, 정확히 하나의 자식을 가지는 노드들의 체인을 나타내고, 다음과 같이 저장하는 대신:

    A -> B -> C -> [some other node]

이러한 형식으로 압축된 노드를 저장한다.

    "ABC" -> [some other node]

압축된 노드의 레이아웃은 다음과 같다:

    +----+---+--------+
    |HDR |ABC|chld-ptr|
    +----+---+--------+

https://www.programmersought.com/article/88111029354/


# Basic API

기본적인 API는 엘리먼트를 추가하거나 삭제할 수 있는 간단한 딕셔너리이다. 주목할 만한 유일한 차이점은 삽입과 삭제 API가 키에 저장된 이전 값을 참조(reference)로 반환하기 위해서 추가적인 인자를 전달받을 수 있는 것이다.

## Creating a radix tree and adding a key

새로운 radix tree는 다음과 같이 생성된다:

    rax *rt = raxNew();

새로운 키를 입력하기 위해서, 다음의 함수를 사용한다:

    int raxInsert(rax *rax, unsigned char *s, size_t len, void *data,
                  void **old);

사용 예:

    raxInsert(rt,(unsigned char*)"mykey",5,some_void_value,NULL);

이 함수는 키가 올바르게 입력되었으면 1을 반환하고, radix tree에 이미 키가 있다면 0을 반환한다: 이 경우에 값이 갱신된다. 메모리 부족(out of memory)일 때에도 0이 값으로 반환되지만, 이 경우에는 `errno`가 `ENOMEM`으로 설정된다.

연관된 값 `data`가 NULL이면, 키가 저장되는 노드는 NULL값을 저장하기 위한 추가적인 메모리를 사용하지 않으므로, 만약 NULL을 연관된 값으로 사용한다면, 키로만 구성되는 딕셔너리들은 메모리 효율성이 높다.

키는 캐릭터(char)의 부호없는 배열이므로, 키의 길이를 지정할 필요가 있다: rax는 바이너리에 안전하기 때문에, 키는 무엇이든지 될 수가 있다.

삽입 함수는 기존의 키 값을 덮어쓰지 않는 변형에 대해서도 사용할 수 있다:

    int raxTryInsert(rax *rax, unsigned char *s, size_t len, void *data,
                     void **old);

이 함수는 정확히 `raxInsert()`와 동일하지만, 만약 키가 존재한다면 이 함수는 (raxInsert와 같이) 이전 값을 건드리지 않고 0을 반환한다. 이전 값은 여전히 이전 포인터를 통해서 참조로 반환할 수 있다.

## Key lookup

검색 함수는 다음과 같다:

    void *raxFind(rax *rax, unsigned char *s, size_t len);

이 함수는 접근하려는 키가 그곳에 없다면 `raxNotFound`라는 특별한 값을 반환한다. 예제는 다음과 같다:

    void *data = raxFind(rax,mykey,mykey_len);
    if (data == raxNotFound) return;
    printf("Key value is %p\n", data);

`raxFind()`는 읽기 전용의 함수라서 메모리 부족 상태는 발생할 수 없고, 그래서 절대 실패하지 않는다.

## Deleting keys

키를 삭제하는 것은 당신이 상상하는대로이지만, 키와 연관된 값을 참조로 반환하는 기능을 이용해서 삭제를 할 수 있다:

    int raxRemove(rax *rax, unsigned char *s, size_t len, void **old);

이 함수는 키를 삭제하면 1을 반환하고, 키가 그곳에 없는 경우에는 0을 반환한다. 또한, 이 함수는 메모리 부족으로 실패하지는 않지만, 키가 삭제되는 동안에 메모리 부족 상태라면, 가능하더라도 결과 트리 노드는 재압축되지 않을 수도 있다: radix tree는 이러한 경우에는 덜 효율적으로 인코딩될 수 있다.

`old` 인자는 선택적인데, 만약 이것이 전달이 된다면, 함수가 성공적으로 키를 찾아 지울 때, 연관된 값의 키가 설정될 것이다.


# Iterators

Rax의 키 스페이스는 사전순서로 정렬되고, 두 개의 키 중에서 더 큰 것을 결정하기 위해서 바이트의 값을 이용해서 키가 구성된다. 만약 키의 접두사가 같으면, 더 긴 키를 더 큰 것으로 간주한다.

Rax 반복자(iterator)는 서로 다른 연산자를 기준으로 주어진 엘리먼트를 찾을 수 있고, 그리고 나서 `raxNext()`와 `raxPrev()`를 호출해서 키 스페이스를 탐색할 수 있다.

## Basic iterator usage

반복자는 일반적으로 스택에 할당되는 로컬 변수로 선언되고, 그 다음 `raxStart` 함수로 초기화된다:

    raxIterator iter;
    raxStart(&iter, rt); // Note that 'rt' is the radix tree pointer.

이 `raxStart` 함수는 절대 실패하지 않고, 값을 반환하지도 않는다. 한번 반복자가 초기화되면, 지정된 위치로부터 반복을 시작하기 위해서 탐색을 할 수 있다. 이를 위해서, `raxSeek`을 사용한다:

    int raxSeek(raxIterator *it, unsigned char *ele, size_t len, const char *op);

예를 들어, `"foo"`와 같거나 큰 첫 번째 요소는 다음과 같이 찾을 수 있다.

    raxSeek(&iter,">=",(unsigned char*)"foo",3);

이 `raxSeek()` 함수는 성공할 때 1을 반환하며, 실패하면 0을 반환한다. 실패할 수 있는 경우는 다음과 같다:

1. 유효하지 않은 연산자가 마지막 인자로 전달되었다.
2. 반복자를 찾는 동안에 메모리 부족 상태가 발생했다. 

반복자가 검색되면, 다음의 예제와 같이 `raxNext`와 `raxPrev` 함수를 이용해서 반복하는 것이 가능하다.

    while(raxNext(&iter)) {
        printf("Key: %.*s\n", (int)iter.key_len, (char*)iter.key);
    }

`raxNext`함수는 `raxSeek`으로 탐색된 엘리먼트로부터 시작하고, 트리의 마지막 엘리먼트까지의 엘리먼트들을 반환한다. 엘리먼트가 더 이상 없을 때애는 0이 반환되고, 그렇지 않으면 1이 반환된다. 그러나 이 함수는 메모리 부족 상태일 때에도 0을 반환할 수 있다: 항상 스택을 사용하기 위해서 시도하지만, 만약 트리의 깊이가 크거나 키가 크다면 반복자는 힙에 할당된 메모리를 사용하기 시작한다.

`raxPrev` 함수는 정확하게 동일한 방식으로 동작하지만, radix tree의 마지막 노드를 향해서 이동하는 대신에 첫 번째 노드를 향해서 이동할 것이다.

# Releasing iterators

An iterator can be used multiple times, and can be sought again and again using `raxSeek` without any need to call `raxStart` again. However, when the iterator is not going to be used again, its memory must be reclaimed with the following call:

    raxStop(&iter);

Note that even if you do not call `raxStop`, most of the times you'll not detect any memory leak, but this is just a side effect of how the Rax implementation works: most of the times it will try to use the stack allocated data structures. However for deep trees or large keys, heap memory will be allocated, and failing to call `raxStop` will result into a memory leak.

## Seek operators

The function `raxSeek` can seek different elements based on the operator. For instance in the example above we used the following call:

    raxSeek(&iter,">=",(unsigned char*)"foo",3);

In order to seek the first element `>=` to the string `"foo"`. However other operators are available. The first set are pretty obvious:

* `==` seek the element exactly equal to the given one.
* `>` seek the element immediately greater than the given one.
* `>=` seek the element equal, or immediately greater than the given one.
* `<` seek the element immediately smaller than the given one.
* `<=` seek the element equal, or immediately smaller than the given one.
* `^` seek the smallest element of the radix tree.
* `$` seek the greatest element of the radix tree.

When the last two operators, `^` or `$` are used, the key and key length argument passed are completely ignored since they are not relevant.

Note how certain times the seek will be impossible, for example when the radix tree contains no elements or when we are asking for a seek that is not possible, like in the following case:

    raxSeek(&iter,">",(unsigned char*)"zzzzz",5);

We may not have any element greater than `"zzzzz"`. In this case, what happens is that the first call to `raxNext` or `raxPrev` will simply return zero, so no elements are iterated.

## Iterator stop condition

Sometimes we want to iterate specific ranges, for example from AAA to BBB. In order to do so, we could seek and get the next element. However we need to stop once the returned key is greater than BBB. The Rax library offers the `raxCompare` function in order to avoid you need to code the same string comparison function again and again based on the exact iteration you are doing:

    raxIterator iter;
    raxStart(&iter);
    raxSeek(&iter,">=",(unsigned char*)"AAA",3); // Seek the first element
    while(raxNext(&iter)) {
        if (raxCompare(&iter,">",(unsigned char*)"BBB",3)) break;
        printf("Current key: %.*s\n", (int)iter.key_len,(char*)iter.key);
    }
    raxStop(&iter);

The above code shows a complete range iterator just printing the keys traversed by iterating.

The prototype of the `raxCompare` function is the following:

    int raxCompare(raxIterator *iter, const char *op, unsigned char *key, size_t key_len);

The operators supported are `>`, `>=`, `<`, `<=`, `==`. The function returns 1 if the current iterator key satisfies the operator compared to the provided key, otherwise 0 is returned.

## Checking for iterator EOF condition

Sometimes we want to know if the itereator is in EOF state before calling raxNext() or raxPrev(). The iterator EOF condition happens when there are no more elements to return via raxNext() or raxPrev() call, because either raxSeek() failed to seek the requested element, or because EOF was reached while navigating the tree with raxPrev() and raxNext() calls.

This condition can be tested with the following function that returns 1 if EOF was reached:

    int raxEOF(raxIterator *it);

## Modifying the radix tree while iterating

In order to be efficient, the Rax iterator caches the exact node we are at, so that at the next iteration step, it can start from where it left. However an iterator has sufficient state in order to re-seek again in case the cached node pointers are no longer valid. This problem happens when we want to modify a radix tree during an iteration. A common pattern is, for instance, deleting all the elements that match a given condition.

Fortunately there is a very simple way to do this, and the efficiency cost is only paid as needed, that is, only when the tree is actually modified. The solution consists of seeking the iterator again, with the current key, once the tree is modified, like in the following example:

    while(raxNext(&iter,...)) {
        if (raxRemove(rax,...)) {
            raxSeek(&iter,">",iter.key,iter.key_size);
        }
    }

In the above case we are iterating with `raxNext`, so we are going towards lexicographically greater elements. Every time we remove an element, what we need to do is to seek it again using the current element and the `>` seek operator: this way we'll move to the next element with a new state representing the current radix tree (after the change).

The same idea can be used in different contexts, considering the following:

* Iterators need to be sought again with `raxSeek` every time keys are added or removed while iterating.
* The current iterator key is always valid to access via `iter.key_size` and `iter.key`, even after it was deleted from the radix tree.

## Re-seeking iterators after EOF

After iteration reaches an EOF condition since there are no more elements to return, because we reached one or the other end of the radix tree, the EOF condition is permanent, and even iterating in the reverse direction will not produce any result.

The simplest way to continue the iteration, starting again from the last element returned by the iterator, is simply to seek itself:

    raxSeek(&iter,iter.key,iter.key_len,"==");

So for example in order to write a command that prints all the elements of a radix tree from the first to the last, and later again from the last to the first, reusing the same iterator, it is possible to use the following approach:

    raxSeek(&iter,"^",NULL,0);
    while(raxNext(&iter,NULL,0,NULL))
        printf("%.*s\n", (int)iter.key_len, (char*)iter.key);

    raxSeek(&iter,"==",iter.key,iter.key_len);
    while(raxPrev(&iter,NULL,0,NULL))
        printf("%.*s\n", (int)iter.key_len, (char*)iter.key);

## Random element selection

To extract a fair element from a radix tree so that every element is returned with the same probability is not possible if we require that:

1. The radix tree is not larger than expected (for example augmented with information that allows elements ranking).
2. We want the operation to be fast, at worst logarithmic (so things like reservoir sampling are out since it's O(N)).

However a random walk which is long enough, in trees that are more or less balanced, produces acceptable results, is fast, and eventually returns every possible element, even if not with the right probability.

To perform a random walk, just seek an iterator anywhere and call the following function:

    int raxRandomWalk(raxIterator *it, size_t steps);

If the number of steps is set to 0, the function will perform a number of random walk steps between 1 and two times the logarithm in base two of the number of elements inside the tree, which is often enough to get a decent result. Otherwise, you may specify the exact number of steps to take.

## Printing trees

For debugging purposes, or educational ones, it is possible to use the following call in order to get an ASCII art representation of a radix tree and the nodes it is composed of:

    raxShow(mytree);

However note that this works well enough for trees with a few elements, but becomes hard to read for very large trees.

The following is an example of the output raxShow() produces after adding the specified keys and values:

* alligator = (nil)
* alien = 0x1
* baloon = 0x2
* chromodynamic = 0x3
* romane = 0x4
* romanus = 0x5
* romulus = 0x6
* rubens = 0x7
* ruber = 0x8
* rubicon = 0x9
* rubicundus = 0xa
* all = 0xb
* rub = 0xc
* ba = 0xd

```
[abcr]
 `-(a) [l] -> [il]
               `-(i) "en" -> []=0x1
               `-(l) "igator"=0xb -> []=(nil)
 `-(b) [a] -> "loon"=0xd -> []=0x2
 `-(c) "hromodynamic" -> []=0x3
 `-(r) [ou]
        `-(o) [m] -> [au]
                      `-(a) [n] -> [eu]
                                    `-(e) []=0x4
                                    `-(u) [s] -> []=0x5
                      `-(u) "lus" -> []=0x6
        `-(u) [b] -> [ei]=0xc
                      `-(e) [nr]
                             `-(n) [s] -> []=0x7
                             `-(r) []=0x8
                      `-(i) [c] -> [ou]
                                    `-(o) [n] -> []=0x9
                                    `-(u) "ndus" -> []=0xa
```

# Running the Rax tests

To run the tests try:

    $ make
    $ ./rax-test

To run the benchmark:

    $ make
    $ ./rax-test --bench

To test Rax under OOM conditions:

    $ make
    $ ./rax-oom-test

The last one is very verbose currently.

In order to test with Valgrind, just run the tests using it, however if you want accurate leaks detection, let Valgrind run the *whole* test, since if you stop it earlier it will detect a lot of false positive memory leaks. This is due to the fact that Rax put pointers at unaligned addresses with `memcpy`, so it is not obvious where pointers are stored for Valgrind, that will detect the leaks. However, at the end of the test, Valgrind will detect that all the allocations were later freed, and will report that there are no leaks.

# Debugging Rax

While investigating problems in Rax it is possible to turn debugging messages on by compiling with the macro `RAX_DEBUG_MSG` enabled. Note that it's a lot of output, and may make running large tests too slow.

In order to active debugging selectively in a dynamic way, it is possible to use the function raxSetDebugMsg(0) or raxSetDebugMsg(1) to disable/enable debugging.

A problem when debugging code doing complex memory operations like a radix tree implemented the way Rax is implemented, is to understand where the bug happens (for instance a memory corruption). For that goal it is possible to use the function raxTouch() that will basically recursively access every node in the radix tree, itearting every sub child. In combination with tools like Valgrind, it is possible then to perform the following pattern in order to narrow down the state causing a give bug:

1. The rax-test is executed using Valgrind, adding a printf() so that for the fuzz tester we see what iteration in the loop we are in.
2. After every modification of the radix tree made by the fuzz tester in rax-test.c, we add a call to raxTouch().
3. Now as soon as an operation will corrupt the tree, raxTouch() will detect it (via Valgrind) immediately. We can add more calls to narrow the state.
4. At this point a good idea is to enable Rax debugging messages immediately before the moment the tree is corrupted, to see what happens. This can be achieved by adding a few "if" statements inside the code, since we know the iteration that causes the corruption (because of step 1).

This method was used with success during rafactorings in order to debug the introduced bugs.