# quicklist

- 작성일: 2019-02-06
- layout: post
- title: "quicklist encoding"
- tags: [code]


## quicklist에 대해서
- Linked List of ziplists
- 레디스 3.2 버전 이전에는 리스트 자료구조에 대해 다음의 두 가지 인코딩 타입이 있었다.
    - `REDIS_ENCODING_ZIPLIST`
    - `REDIS_ENCODING_LINKEDLIST`
- 레디스 3.2 버전부터 두 가지 인코딩은 모두 `REDIS_ENCODING_QUICKLIST`으로 대체되었다.
- 인코딩 타입에 대한 설정 변수도 기존의 것은 삭제 또는 용도가 변경되었고, 새로운 변수도 하나 추가되었다.
    - `list-max-ziplist-entries` (용도 변경)
        - The number of entries allowed per internal list node can be specified as a fixed maximum size or a maximum number of elements.
    - `list-max-ziplist-value` (삭제)
    - `list-compress-depth` (추가)
        - Compress depth is the number of quicklist ziplist nodes from *each* side of the list to *exclude* from compression.


## 핵심 아이디어
- make linked list (fat) of ziplists (compact).
- 즉, linked list내의 각 노드를 ziplists로 구성, 각각의 노드에는 하나 이상의 엘리먼트를 저장하도록 하는 것이다.
- ziplist의 저장 공간 효율성을 취할 수 있고, linkedlist의 성능적인 면을 취할 수 있다.


## linked list
- 링크드 리스트 노드 하나에 데이터를 저장할 때, 부가적으로 추가되는 데이터의 사이즈가 더 큰 경우가 많다.
    - 다음 노드, 이전 노드에 대한 포인터


## ziplist
- 포인터 대신, 앞 뒤 엔트리에 대한 길이 정보를 가져, 엔트리 각각을 구분한다.
- 각각의 엔트리는 prevlen(1,5bytes), ifself let(1,2,5bytes)
- 데이터는 문자열 그대로 저장


## 참고자료
- https://matt.sh/redis-quicklist
- https://github.com/antirez/redis/pull/2143
- http://redisgate.kr/redis/configuration/internal_quicklist.php