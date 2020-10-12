# 1. Memory와 swap

### slab 할당자
기본적으로 리눅스는 페이지를 4kb 단위로 할당하는데, 커널이 쓰기에는 다소 많을 수도 있다. 이 4kb를 slab 단위로 더 잘게 나누어 사용하는 것이 slab 할당자.

### Swap Cache
어떤 메모리 페이지를 스왑 인(swap in) 한 후에도 물리 디스크의 스왑 영역에는 같은 데이터가 남아 있다. 이런 상태의 메모리 페이지는 `스왑 캐시`라고 불리는 리스트에 등록된다. 스왑 캐시에 등록된 메모리 페이지를 다시 스왑 아웃할 필요가 있을 때는 스왑 영역에 남아 있는 동일한 데이터를 이용함으로써 스왑 영역에 쓰기 처리를 생략할 수 있다.
  1. 해당 스왑 영역에 다른 데이터가 스왑 아웃되어 있거나 
  2. 스왑 인된 메모리의 데이터가 바뀐 경우, 스왑 캐시의 등록은 해제된다.

스왑 캐시는 기본적으로 메모리(RAM)의 영역에 위치한다.

음.. 다시 정리한다.

스왑 캐시에 대해서는 각각 swap in, out 에 대해서 동작이 다르다.
1. swap out
   - anon 페이지를 swap 영역에 쓰는 과정에서
     - 먼저, anon 페이지를 프로세스의 페이지 테이블?리스트로부터 해지한다.
     - 이 상태에서 swap 엔트리에 등록하는 것으로 스왑 캐시가 완성
   - swap캐시의 페이지를 swap 영역에 기록한다.
   - swap캐시의 페이지를 참조하는 곳이 없다면 재할당 (버디 시스템으로 gogo)
     - 동시성 문제: 동시에 여러 프로세스 등등에서 이 스왑 캐시 페이지로 접근할 수 있다.
     - 이러한 경우, swap out시의 스왑 캐시가 효과적으로 작용한다.
2. swap in
   - 스왑 영역으로부터 페이지를 읽을 때
   - 먼저, 스왑 영역으로부터 스왑 캐시로 페이지를 옮긴다.
   - 이때, 스왑 영역의 페이지는 삭제하지 않는다.
   - 스왑 캐시된 페이지를 스왑 캐시 엔트리로 등록하고 프로세스에 반환한다.
     - 아마도 이 단계에서는 계속 page fault 가 발생할 것 같다.
     - 스왑이지만 스왑이 아닌 상태?
   - 이 스왑된 페이지가 수정(dirty)가 되거나, swap 영역에 다른 데이터가 쓰여지만 스왑 캐시된 페이지는 제거된다.


페이징이 지속적으로 발생하지 않는 상황에서, swap 사용률이 100%라도, 스왑 캐시 사용률이 높다면..
실제 disk I/O는 발생하지 않을 수도 있다.

## Reference
- http://jake.dothome.co.kr
- http://wiki.kldp.org/Translations/html/The_Linux_Kernel-KLDP



https://github.com/torvalds/linux/blob/7c2a69f610e64c8dec6a06a66e721f4ce1dd783a/include/linux/mmzone.h#L246
```c
enum lru_list {
	LRU_INACTIVE_ANON = LRU_BASE,
	LRU_ACTIVE_ANON = LRU_BASE + LRU_ACTIVE,
	LRU_INACTIVE_FILE = LRU_BASE + LRU_FILE,
	LRU_ACTIVE_FILE = LRU_BASE + LRU_FILE + LRU_ACTIVE,
	LRU_UNEVICTABLE,
	NR_LRU_LISTS
};
```

이 lru_list의 순서가 재할당의 접근 순서가 될 것이다.


https://discuss.aerospike.com/t/how-to-tune-the-linux-kernel-for-memory-performance/4195