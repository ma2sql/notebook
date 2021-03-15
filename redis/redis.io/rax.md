# Rax, an ANSI C radix tree implementation
Rax는 radix tree의 구현이고, 초기에는 성능상의 이슈를 해결하기 위해서 레디스의 특정한 위치에서 사용하기 위한 목적으로 작성되었지만, 레디스 내부, 또는 외부에서 만들어지는 어플리케이션, 그리고 기타 다른 프로젝트에서도 재사용이 될 수 있도록, 곧바로 독립된 프로젝트로 변경되었다.

주요 목적은 적절한 밸런스를 찾는 것이며, 동시에 다양한 요구사항에 대처할 수 있도록 완전한 구현된 radix tree를 제공하는 것이다.

이 라이브러리를 개발하는 동안에 radix tree가 얼마나 실용적이고 적용가능한지에 대해 점점 더 흥미를 느꼈고, 또 특히 유연한 이터레이터를 포함해서 완전한 기능을 갖춘 radix tree를 견고하게 구현하는 것이 얼마나 어려운지를 알게 되어 매우 놀랐다. 노드를 분할하거나, 병합, 또 다양한 엣지 케이스 등 많은 것들이 잘못될 수 있다. 이러한 이유로 이 프로젝트의 주 목적은 사람들이 이 구현을 사용하고, 또 버그의 수정을 공유할 수 있도록 안정적이고 잘 테스트된(battle tested) 구현을 제공하는 것이다. 이 프로젝트는 모든 코드의 라인 뿐만 아니라 가능한 많은 상태에 대해서도 조사하기 위해서 퍼지 테스트 테크닉에 많이 의존한다. 

Rax는 오픈 소스 프로젝트이고, BSD의 2-calue 라이센스로 릴리즈되었다.

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
    + (트리가 수정되는 동안 이터레이터를 사용하는 방법을 포함하는) 이터레이터(또는 이터레이터). 
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
* 퍼지 테스트를 이용한 광범위한 코드와 있을 수 있는 상태에 대한 테스트 커버리지 (Extensive code and possible states test coverage using fuzz testing)
    + 테스트는 일반적이지 않은 상태를 탐색하기 위한 퍼징에 많이 의존한다.
    + 단순한 해시 테이블과 정렬된 배열의 동일한 행동의 구현과 비교되는 딕셔너리와 이터레이터의 구현. 랜덤한 데이터를 생성하고 2개의 구현의 결과가 맞는지 체크한다.
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

Rax 이터레이터(iterator)는 서로 다른 연산자를 기준으로 주어진 엘리먼트를 찾을 수 있고, 그리고 나서 `raxNext()`와 `raxPrev()`를 호출해서 키 스페이스를 탐색할 수 있다.

## Basic iterator usage

이터레이터는 일반적으로 스택에 할당되는 로컬 변수로 선언되고, 그 다음 `raxStart` 함수로 초기화된다:

    raxIterator iter;
    raxStart(&iter, rt); // Note that 'rt' is the radix tree pointer.

이 `raxStart` 함수는 절대 실패하지 않고, 값을 반환하지도 않는다. 한번 이터레이터가 초기화되면, 지정된 위치로부터 반복을 시작하기 위해서 탐색을 할 수 있다. 이를 위해서, `raxSeek`을 사용한다:

    // wrong!
    // int raxSeek(raxIterator *it, unsigned char *ele, size_t len, const char *op);
    int raxSeek(raxIterator *it, const char *op, unsigned char *ele, size_t len);

예를 들어, `"foo"`와 같거나 큰 첫 번째 요소는 다음과 같이 찾을 수 있다.

    raxSeek(&iter,">=",(unsigned char*)"foo",3);

이 `raxSeek()` 함수는 성공할 때 1을 반환하며, 실패하면 0을 반환한다. 실패할 수 있는 경우는 다음과 같다:

1. 유효하지 않은 연산자가 마지막 인자로 전달되었다.
2. 이터레이터를 찾는 동안에 메모리 부족 상태가 발생했다. 

이터레이터가 검색되면, 다음의 예제와 같이 `raxNext`와 `raxPrev` 함수를 이용해서 반복하는 것이 가능하다.

    while(raxNext(&iter)) {
        printf("Key: %.*s\n", (int)iter.key_len, (char*)iter.key);
    }

`raxNext`함수는 `raxSeek`으로 탐색된 엘리먼트로부터 시작하고, 트리의 마지막 엘리먼트까지의 엘리먼트들을 반환한다. 엘리먼트가 더 이상 없을 때애는 0이 반환되고, 그렇지 않으면 1이 반환된다. 그러나 이 함수는 메모리 부족 상태일 때에도 0을 반환할 수 있다: 항상 스택을 사용하기 위해서 시도하지만, 만약 트리의 깊이가 크거나 키가 크다면 이터레이터는 힙에 할당된 메모리를 사용하기 시작한다.

`raxPrev` 함수는 정확하게 동일한 방식으로 동작하지만, radix tree의 마지막 노드를 향해서 이동하는 대신에 첫 번째 노드를 향해서 이동할 것이다.

# Releasing iterators

이터레이터는 여러 번 사용될 수 있고, `raxStart`를 다시 호출할 필요가 없이 `raxSeek`을 이용해서 몇 번이고 다시 검색될 수 있다. 그러나, 이터레이터가 다시 사용되지 않을 때, 그것의 메모리는 다음을 호출해서 회수해야 한다.

    raxStop(&iter);

심지어 당신이 `raxStop`을 호출하지 않더라도, 대부분 당신은 어떠한 메모리 누수도 발견할 수 없을 것이지만, 이것은 단지 Rax의 구현이 작동하는 방식의 부수 효과(side effect)일 뿐이다: 스택에 할당된 자료 구조를 사용하려고 시도한다. 그러나 깊은 트리나 큰 기에 대해서, 힙 메모리가 할당되고, `raxStop`의 호출 실패는 메모리 누수로 이어진다.

## Seek operators

`raxSeek` 함수는 연산자에 따라서 각각 다른 요소를 검색할 수 있다. 예를 들어, 위의 예제에서 우리는 다음과 같이 호출했다.

    raxSeek(&iter,">=",(unsigned char*)"foo",3);

`>=`로 문자열 `"foo"`에 대한 첫 엘리먼트를 찾기 위함이다. 그러나 다른 연산자도 사용할 수 있다. 첫 번재 셋은 아주 명백하다.

* `==`는 주어진 것과 정확히 같은 엘리먼트를 검색한다.
* `>`는 주어진 것보다 큰 (첫번쪠) 엘리먼트를 검색한다.
* `>=`는 주어진 것보다 같거나 큰 (첫번쪠) 엘리먼트 검색한다.
* `<`는 주어진 것보다 작은 (첫번쪠) 엘리먼트를 검색한다.
* `<=`는 주어진 것보다 같거나 작은 (첫번쪠) 엘리먼트를 반환한다.
* `^`는 radix tree내에서 가장 작은 엘리먼트를 반환한다.
* `$`는 radix tree내에서 가장 큰 엘리먼트를 반환한다.

마지막 두 연사자 `^`나 `$`가 사용되면, 전달된 키와 키의 길이에 대한 인자는 관련이 없기 때문에 완전히 무시된다.

예를 들어, radix tree가 어떤 엘리먼트도 포함하지 않거나, 또는 다음과 같이 찾을 수 없는 것으로 검색을 시도할 때에는, 탐색이 불가능할 수가 있다는 것에 주의해야 한다:

    raxSeek(&iter,">",(unsigned char*)"zzzzz",5);

`"zzzzz"`보다 더 큰 엘리먼트는 없을지도 모른다. 이러한 경우에는 첫 번째 `raxNext`또는 `raxPrev`호출은 단순히 0을 반환할 것이고, 따라서 반복되는 엘리먼트는 없다.

## Iterator stop condition

때때로 우리는 AAA에서 BBB처럼, 특정 범위를 반복하기를 원할 것이다. 그렇게 하기 위해서, 탐색(seek)하고, 다음 원소를 찾는다. 그러나 키가 BBB보다 큰 값을 반환하면 멈춰야한다. Rax라이브러리는 수행중인 정확한(exact) 반복을 기반으로 동일한 문자열 비교 함수를 되풀이하지 않도록 `raxCompare` 함수를 제공한다.

    raxIterator iter;
    raxStart(&iter);
    raxSeek(&iter,">=",(unsigned char*)"AAA",3); // Seek the first element
    while(raxNext(&iter)) {
        if (raxCompare(&iter,">",(unsigned char*)"BBB",3)) break;
        printf("Current key: %.*s\n", (int)iter.key_len,(char*)iter.key);
    }
    raxStop(&iter);

위의 코드는 반복에 의해 탐색된 키를 출력하기만 하는 전체 범위에 대한 이터레이터를 보여준다.

`raxCompare` 함수의 프로토타입은 다음과 같다:

    int raxCompare(raxIterator *iter, const char *op, unsigned char *key, size_t key_len);

연산자는 `>`, `>=`, `<`, `<=`, `==`가 지원된다. 함수는 현재의 이터레이터 키가 전달된 키와 비교하여 연산자를 만족하면 1을 반환하고, 그렇지 않으면 0을 반환한다.

## Checking for iterator EOF condition

때때로 우리는 `raxNext()`나 `raxPrev()`를 호출하기 전에, 이터레이터가 EOF 상태인지 알고 싶어할 수 있다. `raxSeek()`가 요청한 엘리먼트를 찾는 것에 실패했기 때문에거나, 또는 EOF가 `raxPrev()`나 `raxNext()`로 트리를 탐색하는 동안에 EOF에 다다랐기 때문에, `raxNext()`나 `raxPrev()` 호출로 더 이상 반환할 엘리먼트가 없을 때 이터레이터 EOF 상태가 발생한다.

이 상태는 다음의 함수로 테스트될 수 있고, EOF에 다다랐다면 1을 반환한다:

    int raxEOF(raxIterator *it);

## Modifying the radix tree while iterating

효율을 위해서, Rax의 이터레이터는 현재 위차한 정확한 노드를 캐시하고, 그래서 다음 단계에서는 그 왼쪽에서부터 시작할 수 있다. 그러나 캐시된 노드 포인터가 더 이상 유효하지 않은 경우에 이터레이터는 다시 검색을 하기 위한 충분한 상태를 가진다. 이 문제는 우리가 반복하는 동안에 radix tree를 변경하려고 할 때 발생한다. 일반적인 패턴은, 예를 들어, 주어진 조건에 일치하는 모든 엘리먼트를 삭제하는 것이다.

다행스럽게도 이를 위한 매우 간단한 방법이 있고, 효율성에 대한 비용은 필요한만큼만 지불하면 되는데, 그것은 트리가 실제로 변경되는 경우에만이다. 해결책으로는 다음의 예처럼 트리가 변경될 때에 현재 키로 다시 이터레이터를 찾는 것으로 이루어진다:

    while(raxNext(&iter,...)) {
        if (raxRemove(rax,...)) {
            raxSeek(&iter,">",iter.key,iter.key_size);
        }
    }

위의 경우에서 `raxNext`로 반복하고 있기 때문에, 사전적으로 더 큰 엘리먼트를 향해서 가게 된다. 엘리먼트를 삭제할 때마다 현재의 엘리먼트와 `>` 탐색 연산자를 이용해서 재탐색을 할 필요가 있다: 이러한 방법으로 (변경된 후) 현재의 radix tree를 나타내는 새로운 상태의 다음 엘리먼트로 이동할 수 있다.

다음과 같은 것을 고려하면, 같은 아이디어가 다른 문맥에서도 사용될 수 있다:

* 반복되는 동안 키가 추가되거나 삭제될 때마다, 이터레이터는 `raxSeek`으로 다시 탐색될 필요가 있다.
* 현재의 이터레이터는 raidx tree에서 키가 삭제된 이후라도 `iter.key_size`와 `iter.key`를 통해서 접근할 수 있다.

## Re-seeking iterators after EOF

더 이상 반환하는 엘리먼트가 없기 때문에 반복이 EOF 상태에 다다른 이후에는, radix tree의 한 쪽 또는 다른 쪽의 끝에 도달했기 때문에 EOF 상태는 영구적이고, 심지어 반대 방향으로의 반복 역시 어떠한 결과도 만들어내지 않는다.

이터레이터가 반환한 가장 마지막 엘리먼트로부터 다시 시작하여, 반복을 계속하기 위한 가장 단순한 방법은 단순히 자기 자신을 탐색하는 것이다:

    raxSeek(&iter,iter.key,iter.key_len,"==");

예를 들어, 동일한 이터레이터를 재사용해서 radix tree의 모든 엘리먼트를 처음부터 마지막까지, 그리고 다시 마지막에서 처음까지를 출력하는 커맨드를 작성하기 위해서 다음과 같은 접근법을 사용할 수 있다:

    raxSeek(&iter,"^",NULL,0);
    while(raxNext(&iter,NULL,0,NULL))
        printf("%.*s\n", (int)iter.key_len, (char*)iter.key);

    raxSeek(&iter,"==",iter.key,iter.key_len);
    while(raxPrev(&iter,NULL,0,NULL))
        printf("%.*s\n", (int)iter.key_len, (char*)iter.key);

## Random element selection

필요한 경우에 radix tree에서 공평한 엘리먼트 추출하는 것, 즉, 모든 엘리먼트가 동일한 가능성으로 반환되는 것은 가능하지 않다:

1. radix tree는 예상보다 크지 않다. (예를 들어, 랭킹을 매길 수 있을만한 정보가 증강되면)
2. 최악의 경우라도 로거리듬 정도로 오퍼레이션은 빨라야한다. (그래서 reservoir sampling와 같은 것들은 O(N)이기 때문에 제외된다.)

그러나 거의 균형적인 트리에서 충분히 긴 랜덤 워크(walk)는 수용 가능한 결과를 만들어내고, 빠르고, 심지어 정확한 확률은 아니더라도 결국 모든 가능한 엘리먼트를 반환한다. 

랜덤 워크를 수행하기 위해서, 단순히 어디서든 이터레이터를 찾고, 다음의 함수를 호출한다:

    int raxRandomWalk(raxIterator *it, size_t steps);

만약 스텝의 수를 0으로 설정한다면, 함수는 트리의 내에서 밑이 2인 로그의 1~2배 사이의 수로 랜덤 워크를 수행하며, 종종 적절한 결과를 얻기에는 충분하다. 그렇지 않은 경우에는 정확한 스텝의 수를 지정할 수 있다.

## Printing trees

디버깅을 목적으로, 또는 교육의 목적으로, adix tree와 노드의 구성을 ASCII 아트의 표현을 출력하기 위해서 다음과 같이 호출할 수 있다:

    raxShow(mytree);

그러나 이것은 엘리먼트가 얼마 없는 트리에 대해서는 충분히 잘 동작하지만, 매우 큰 트리는 읽기가 어렵다.

다음은 지정된 키와 값을 추가한 이후에 생성되는 `raxShow()` 출력의 예이다:

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

테스트를 실행하려면 다음을 시도한다:

    $ make
    $ ./rax-test

벤치마크를 수행하라면:

    $ make
    $ ./rax-test --bench

OOM 조건 아래에서 Rax를 테스트하려면:

    $ make
    $ ./rax-oom-test

마지막의 것은 현재 매우 장황하다.

Valgrind로 테스트하기 위해서, 단순히 그것을 이용해서 테스트를 실행한다. 그러나 정확한 릭을 감지하기를 원한다면, Valgrind로 *전체(whole)* 테스트를 실행하는데, 만약 더 일찍 중지시키면, 많은 수의 잘못된 양수의 메모리 릭(false positive memory leak)을 감지할 것이기 때문이다. 이것은 Rax가 `memcpy`로 정렬되지 않은 주소에 포인터를 두는 사실 때문이고, 그래서 Valgrind에 의해서 메모리 릭이 감지될 포인터가 저장되는 장소는 명확하지 않다. 그러나 테스트의 끝에서, Valgrind는 모든 할당이 나중에 해제된 것을 감지할 것이고, 메모리 릭이 없다고 보고할 것이다.

# Debugging Rax

Rax에서 문제를 조사하는 동안 `RAX_DEBUG_MSG` 매크르롤 활성화한 상태에서 컴파일함으로써 디버깅 메시지를 활성화할 수 있다. 매우 많은 출력이 있고, 큰 테스트에 대해서는 아주 느릴 수 있는 것에 주의해야 한다.

동적인 방식으로 선택적으로 디버깅을 활성화하기 위해서, `raxSetDebugMsg(0)`나 `raxSetDebugMsg(1)` 함수를 사용해서 디버깅 비활성/활성을 하는 것이 가능하다.

Rax의 방식으로 구현된 radix tree처럼 복잡한 메모리 조작을 하는 코드를 디버깅할 때에 문제가 되는 것은 (메모리 충돌과 같은) 버그가 발생한 장소를 알아내는 것이다. 이러한 목표를 위해서 기본적으로 재귀적인 방식으로 radix tree의 모든 노드를 접근하고, 모든 하위의 자식 노드를 반복하는 `raxTouch()` 함수를 사용할 수 있다. Valgrind와 같은 툴과의 조합으로, 주어진 버그를 발생시키는 상태를 좁혀나가기 위해서 다음의 패턴으로 디버깅해볼 수 있다:

1. rax-test는 Valgrind를 이용해서 실행되고, `printf()`를 추가해서 퍼즈(fuzz) 테스트에 대해서 루프 내에서 어떤것이 반복되는 확인할 수 있다.
2. rax-test.c 내에서 퍼즈 테스트에 의해 만들어진 radix tree의 매 변경마다, `raxTouch()`를 호출을 추가한다.
3. 이제 오퍼레이션이 트리를 손상시키면, `raxTouch()`는 Valgrind를 통해서 이것을 즉시 감지할 수 있다. 상태를 좁혀가기 위해서 더 많은 호출을 추가할 수 있다.
4. 이 지점에서 좋은 아이디어는 트리가 손상되기 직전에 Rax 디버깅 메시지를 즉시 활성화해서 무엇이 일어나는지를 보는 것이다. 1번 스템으로 손상이 발생하는 반복을 알 수 있기 때문에, 코드 내에 몇 개의 "if"문을 추가하면 이를 달성할 수 있다.

이러한 방법은 소개된 버그를 디버깅하기 위해서 리팩터링하는 동안에 성공적으로 사용되었다.