---
tags: [redis]
---

Offline migration 
======

<!-- TOC -->

- [Mission](#mission)
- [MIGRATE 내부적으로 사용되는 3가지 커맨드](#migrate-내부적으로-사용되는-3가지-커맨드)
- [RESTORE 커맨드에 대한 테스트](#restore-커맨드에-대한-테스트)

<!-- /TOC -->

## Mission
원본 클러스터를 request가 없는 상태에서, 일부의 데이터에 대해서만 대상 클러스터로 옮길 필요가 있다. 다만, 대상 클러스터에 대해서는  지속적으로 request가 처리하고 있는 상태이므로, 마이그레이션 과정에서 대상 서버로 응답 지연을 발생시켜서는 안된다.

- 원본 클러스터: 3.x
- 대상 클러스터: 4.x


## MIGRATE 내부적으로 사용되는 3가지 커맨드
참고: *https://redis.io/commands/migrate*

마이그레이션을 위해 가장 기본적으로는 `MIGRATE` 커맨드를 생각해볼 수가 있는데, big key를 처리하는 것에는 조금 문제가 있다. 그 이유는 MIGRATE 커맨드는 내부적으로 `DUMP` `RESTORE` `DEL` 커맨드를 사용하도록 되어 있기 때문이다. 만약 big key를 옮겨야하는 경우, 각각의 커맨드에 대해서 원본/대상 클러스터에 레이턴시에 영향을 줄 수 있을까?

- `DEL`: MIGRATE 커맨드의 COPY 옵션을 이용하여 회피하는 것이 가능. 4.x 이상이라면 lazy-* 관련 기능을 이용해볼 수 있을 것
- `DUMP`: 슬레이브에서 실행하는 것으로 블로킹 커맨드로 인한 영향도를 줄이는 것이 가능
- `RESTORE`: 대상 서버에서의 블로킹을 회피할 방법이 없어 보임

메뉴얼의 **RESTORE** 커맨드 설명을 보면, 복원해야할 값이 클수록 시간이 많이 소요될 것을 예상할 수가 있다. `DEL`과 `DUMP`에 대해서는 어느 정도 회피책을 가져갈 수 있지만, 아쉽게도 `RESTORE` 에 의한 big key 복원에 대해서는 응답 지연을 피할 수 없어보인다.

```
Available since 2.6.0.
Time complexity: O(1) to create the new key and additional O(N*M) to reconstruct the serialized value, 
where N is the number of Redis objects composing the value and M their average size. 
For small string values the time complexity is thus O(1)+O(1*M) where M is small, so simply O(1). 
However for sorted set values the complexity is O(N*M*log(N)) because inserting values into sorted sets is O(log(N)).
```

## RESTORE 커맨드에 대한 테스트
실제로 `RESTORE` 커맨드로 빅 키 (big key)를 복원할 때 블로킹이 발생할 수 있을까? 간단히 테스트해 본 결과, 블로킹이 발생하고 응답 시간이 지연되는 것을 확인할 수 있었다.

```
memory usage migration_test
269303876
 
r.set('migration_test', 'a'*(2**28))
raw = r.dump('migration_test')
r.restore('migration_test', 0, raw, replace=True)
...
[2019-10-11 15:31:53] called: 6091 / avg: 164.188 us / max: 818.491 us / elapsed: 1000.070 ms 
[2019-10-11 15:31:54] called: 6180 / avg: 161.822 us / max: 822.783 us / elapsed: 1000.058 ms 
# RESTORE 지점에서의 지연 발생
[2019-10-11 15:31:55] called: 977 / avg: 1023.690 us / max: 838563.442 us / elapsed: 1000.145 ms 
[2019-10-11 15:31:56] called: 5872 / avg: 170.304 us / max: 3812.551 us / elapsed: 1000.026 ms 
[2019-10-11 15:31:57] called: 5748 / avg: 174.152 us / max: 3784.657 us / elapsed: 1001.024 ms 
[2019-10-11 15:31:58] called: 5956 / avg: 167.915 us / max: 2950.191 us / elapsed: 1000.103 ms
```