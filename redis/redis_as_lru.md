**maxmemory-policy**를 이용하면 redis를 LRU 캐시로도 활용할 수 있다. (참고: [Using Redis as an LRU cache](https://redis.io/topics/lru-cache)). 상대적으로 덜 참조되는 키들은 제거(eviction)하고, 되도록 자주 참조되는 키들을 메모리 상에 남기는 식으로 캐시 히트율을 높여 제한된 메모리 공간을 효율적으로 사용할 수가 있는 것이다.

> redis의 LRU는 "Approximated LRU algorithm"로 LRU를 정확히 구현하고 있지는 않다.
https://redis.io/topics/lru-cache#approximated-lru-algorithm

하지만 이렇게 redis를 LRU 캐시 용도로 사용할 때에는 주의할 점이 하나가 있다. redis는 eviction처리 시에 여유 메모리 공간을 확보할 때까지 이미 존재하는 키들을 어떤 임의의 기준(maxmemory-policy)에 따라 삭제하기를 반복하는데, 문제는 이러한 *eviction loop의 처리 시간이 매우 길어지는 현상*이 생길 수가 있다는 것이고, 이 시점에 redis의 응답 속도는 현저히 느려지거나, 아예 몇 십초간 응답을 멈추게 될 수도 있다는 것이다.

## eviction 처리는 어떻게?
eviction loop가 어떻게 길어지는지를 알아보기 전에, eviction 처리에 대해서 간단히 정리해보자.

eviction 처리는 maxmemory-policy에 따라 삭제할 키를 몇 개 선출(maxmemory-samples 또는 랜덤)하고, 그 중 가장 기준에 잘 부합하는 키(bestkey)를 제거하는 형태로 이루어진다. 그리고 이러한 동작은 필요한 메모리를 확보할 때까지 하나의 loop에서 처리된다.
(참고: https://github.com/redis/redis/blob/25214bd7dc2f4c995d76020e95180eb4e6d51672/src/evict.c#L446)

maxmemory-policy에 따른 삭제 대상 키 선출 기준은 다음과 같다.
* maxmemory-policy가 LRU / LFU / TTL 계열인 경우?
    1. maxmemory-samples에 지정된 수(기본값: 5)만큼 임의의 키를 뽑는다.
    2. 선출된 키를 LRU/LFU/TTL에 따라 정렬하고, 가장 기준을 만족하는 키(bestkey) 하나를 선택해 삭제한다.

* maxmemory-policy가 RANDOM인 경우?
    * 랜덤으로 아무 키 하나를 선택해서 삭제한다.


## 리해싱(rehashing)이란?
리해싱(rehashing)은 redis가 키를 관리하는 해시테이블의 크기를 늘려서 해시 충돌 등으로부터 키 탐색 시간을 느려지지 않게 하기 위한 방법이다. 해시테이블의 크기 4, 즉 4개의 슬롯을 보유하는 것으로부터 시작하며, 관리하는 키의 수보다 큰 *2의 n승 단위*가 될 때마다, 현재보다 2배 더 큰 해시테이블로 리해싱을 하게 된다. 만약, 현재 해시테이블의 크기(슬롯의 수)가 67,108,864(2^26)라면, 그것보다 키가 1개 더 많아지는 시점부터 리해싱이 시작된다.

> rehashing에 대해 상세한 내용은 아래 문서를 참고하자.
https://tech.kakao.com/2016/03/11/redis-scan/

## 리해싱과 eviction의 관계?
리해싱이 시작되면, 먼저 2배 더 큰 새로운 해시테이블을 생성하고, 기존 해시테이블의 키를 조금씩 옮겨나가게 된다. 해시테이블은 해시 슬롯 개수만큼의 배열을 가지고, 이 배열의 길이는 해시테이블의 크기가 된다. 현재의 해시테이블의 크기가 67,108,864(2^26)라고 할 때, 신규 해시테이블의 크기는 2배가 더 큰 134,217,728(2^27)가 된다. 그리고 이 크기만큼의 배열을 새롭게 생성하는데, 각각의 슬롯은 하나 이상의 키를 관리하는 리스트(list)를 가리키는 포인터이므로, 134,217,728 크기의 해시테이블은 64비트 시스템인 경우에 1GB(134,217,728 x 8bytes)가 된다.

문제는 이렇게 리해싱으로 인해 일시적으로 늘어나는 메모리 공간 역시 maxmemory 판단 기준에 포함된다는 것이다. redis가 maxmemory를 판단할 때, 제외하는 메모리 공간은 오직 aof 버퍼와 client-output-buffer(slave)뿐이다.

```
used_memory - AOF_buffer_size - replica_output_buffer_size >= maxmemory
```

*정리하면, 리해싱으로 일시적인 메모리 상승이 있을 수 있고, 이로 인해 여유 메모리 공간을 모두 소진하고 maxmemory를 초과해버릴 수 있다. `SET` 등 후속으로 유입되는 키의 추가 요청에 대해서 eviction 처리가 필요하게 되는데, 한 번의 eviction loop에서 리해싱으로 초과해버린 메모리만큼을 키를 삭제해야하고, 이 처리가 끝날때까지 redis는 응답하지 못하게 되는 것이다.*

## 테스트
아래는 간단한 재현테스트이다. 테스트 요약하면 다음과 같다.
1. maxmemory는 0으로 설정하고, 키를 2^26만큼 생성한다.
2. 현재 사용하는 메모리보다 조금 더 큰 값으로 maxmemory를 설정한다.
3. 키를 하나 생성해서 rehashing을 발생시킨다. (maxmemory를 대략 1GB 초과)
4. 또 다른 세션에서 키 하나를 새롭게 추가하고, 응답 시간을 체크한다.
   
**CLIENT SESSION #1**
```
redis> config set maxmemory 0
redis> debug populate 67108864 prefix 128
redis> info memory
# Memory
used_memory:15490105320
...

redis> config set maxmemory 15491105320
redis> debug htstats 0
[Dictionary HT]
Hash table 0 stats (main hash table):
 table size: 67108864
 ...

redis> set test1 val1
redis> debug htstats 0
[Dictionary HT]
Hash table 0 stats (main hash table):
 table size: 67108864
...
Hash table 1 stats (rehashing target):
 table size: 134217728
...

redis> info memory
# Memory
used_memory:16563847200
...
```

**CLIENT SESSION #2**
```bash
# maxmemory-policy: allkeys-lru
# maxmemory-samples: 5
time redis-cli -p 6379 -h 127.0.0.1 set foo bar
OK

real    0m30.669s
user    0m0.000s
sys     0m0.001s

# maxmemory-policy: allkeys-lru
# maxmemory-samples: 1
time redis-cli -p 6379 -h 127.0.0.1 set foo bar
OK

real    0m18.162s
user    0m0.001s
sys     0m0.000s
 
# maxmemory-policy: allkeys-random
time redis-cli -p 6379 -h 127.0.0.1 set foo bar
OK

real    0m16.650s
user    0m0.000s
sys     0m0.001s
```

단순히 키 하나를 추가하는 것에 최대 30초 정도가 소요된 것을 확인할 수 있다. maxmemory-samples를 1로 줄이거나, maxmemory-policy를 random으로 두어 eviction 처리를 간소화시키면 16~18초까지 소요 시간이 줄였지만, 여전히 매우 긴 시간동안 redis는 응답할 수가 없었다.

## 결론
사실 이 문제가 빈번하지는 않을 것인데, 다음의 2가지 조건을 모두 충족해야하기 때문이다. 

* maxmemory에 아직 다다르지 않은 상태지만 거의 근접한 상황
* 키의 개수가 리해싱 단위 (2의 n승)에 가까워진 경우 (expiring 포함)

또한, 그리고 키의 수가 많으면 많을 수록 임팩트가 클 것인데, 반대로 키의 수가 적을 때에는 크게 눈에 띄지 않을 수도 있고, 아니면 무시 가능한 수준일지도 모르겠다.

직접 redis의 코드를 수정해서 사용하지 않는 이상은 아직까지는 특별히 redis에서 할 수 있는 것은 없어보인다. 다만, 앞서 이야기한 것처럼 리해싱은 2의 n승 단위로 이루어지므로, 현재의 키 개수를 체크하여 2의 n승에 가까워졌을 때, 메모리 여유 공간이 충분한지를 미리 체크하고 필요하다면 maxmemory 제한을 조금 더 올려주는 방식으로 대응을 해볼 수도 있을 것이다.

다행인것은 6.2버전부터는 eviction loop에 제한이 생기는 것 같으나, 이것이 하위 버전으로 백포트될 수 있을지는 아직 모르겠다.
* 관련 PR: https://github.com/redis/redis/pull/7653

## Reference
- https://github.com/redis/redis/issues/2716
- https://blog.twitter.com/engineering/en_us/topics/infrastructure/2019/improving-key-expiration-in-redis.html
- https://tech.kakao.com/2016/03/11/redis-scan/