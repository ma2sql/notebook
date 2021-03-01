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