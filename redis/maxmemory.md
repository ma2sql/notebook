---
tags: [redis]
---

# maxmemory에 도달한 기준은 used_memory? 아니면 used_memory_rss?

## 배경
레디스가 사용중인 메모리가 maxmemory에 도달하면, 레디스 에러로 OOM을 발생시키던지, 아니면 maxmemory-policy에 의해 eviction이 발생할 것이다. `INFO` 커맨드를 통해 확인할 수 있는 현재 메모리 사용량에 대한 정보에는 크게 2가지 항목이 있다.

- used_memory: 현재 사용중인 메모리 사용량
- used_memory_rss: 현재 사용중인 메모리 사용량 (RSS. os 기준)

두 항목 각각에 대한 설명처럼, 두 항목은 각각 다른 기준으로 메모리 사용량을 표기하며, 실제 운영시에도 각각 표기되는 메모리 사용량은 다른 경우가 많다. 사실 대량이 키 삭제 작업 등에 의해 used_memory는 바로 줄어들지만, used_memory_rss는 줄어들지 않는 것으로 볼 때, 당연히 used_memory 가 기준이 되는 것이 당연해보인다. 하지만 역시 엔지니어 입장에서는 더욱 확실한 근거가 필요할 것이라 생각하니, 소스 코드를 통해 정확히 어떤 부분이 사용되는지를 알아본다.

## 소스 코드 읽어보기
단순하게 접근한다. `INFO` 커맨드로 출력된 텍스트 그대로 검색해보고, 어차피 어느 부분에서는 print를 찍어내는 것을 찾는다. 그곳이 바로 **server.c** 이다.

### server.c
```c
/* Create the string returned by the INFO command. This is decoupled
 * by the INFO command itself as we need to report the same information
 * on memory corruption problems. */
sds genRedisInfoString(char *section) {
    ...
    
    /* Memory */
    if (allsections || defsections || !strcasecmp(section,"memory")) {
        char hmem[64];
        ...

        size_t zmalloc_used = zmalloc_used_memory();
    
        ...

        if (sections++) info = sdscat(info,"\r\n");
        info = sdscatprintf(info,
            "# Memory\r\n"
            "used_memory:%zu\r\n"
            "used_memory_human:%s\r\n"
            "used_memory_rss:%zu\r\n"
            "used_memory_rss_human:%s\r\n"
            ...
            "lazyfree_pending_objects:%zu\r\n",
            zmalloc_used,
            hmem,
            server.cron_malloc_stats.process_rss,
            used_memory_rss_hmem,
```

used_memory는 zmalloc_used, used_memory_rss는 server.cron_malloc_stats.process_rss 를 통해 출력하고 있는 것을 알 수 있다. 그리고 zmalloc_used는 **zmalloc_used_memory()** 호출을 통해 값을 얻어내고 있다. rss는 **server.cron_malloc_stats.process_rss** 값을 바라보고 있다. 참고로 used_memory는 `INFO` command가 호출될 때마다 정보가 새롭게 수집되어 출력하고 있으며 (zmalloc_used_memory가 특정 시간 간격 내에서는 동일한 값을 반환할 가능성은 일단 무시), used_memory_rss의 경우 server.cron_malloc_stats 내의 값을 그대로 호출할 뿐이라는 것도 확인할 수 있다.


```c
int serverCron(struct aeEventLoop *eventLoop, long long id, void *clientData) {
    ...
    run_with_period(100) {
        /* Sample the RSS and other metrics here since this is a relatively slow call.
         * We must sample the zmalloc_used at the same time we take the rss, otherwise
         * the frag ratio calculate may be off (ratio of two samples at different times) */
        server.cron_malloc_stats.process_rss = zmalloc_get_rss();
        server.cron_malloc_stats.zmalloc_used = zmalloc_used_memory();
```

server.cron_malloc_stats.process_rss 가 언제 수집되는지는 server.c의 serverCron에서 확인할 수 있었다. 주석의 설명을 보면 zmalloc_get_rss의 호출이 다른 매트릭에 비해 상대적으로 느리다른 내용이 있다. 이러한 이유로 `INFO` 커맨드 호출 시에는 별도로 zmalloc_get_rss를 호출하는 것 같지는 않다.

그렇다면 어떠한 값을 기준으로 eviction을 수행하는지 다음 코드를 살펴보도록 하자.

### evict.c

maxmemory에 의한 eviction 처리는 evict.c 내의 **freeMemoryIfNeeded** 함수에서 이루어진다. 

```c
int freeMemoryIfNeeded(void) {
    int keys_freed = 0;
    /* By default replicas should ignore maxmemory
     * and just be masters exact copies. */
    if (server.masterhost && server.repl_slave_ignore_maxmemory) return C_OK;

    size_t mem_reported, mem_tofree, mem_freed;
    mstime_t latency, eviction_latency;
    long long delta;
    int slaves = listLength(server.slaves);

    /* When clients are paused the dataset should be static not just from the
     * POV of clients not being able to write, but also from the POV of
     * expires and evictions of keys not being performed. */
    if (clientsArePaused()) return C_OK;
    if (getMaxmemoryState(&mem_reported,NULL,&mem_tofree,NULL) == C_OK)
        return C_OK;
    ...
```

eviction 작업에서 사용할 메모리 정보는 getMaxmemoryState 함수에서 처리된다. 다시 getMaxmemoryState 함수를 살펴보면 다음과 같다.

```c
int getMaxmemoryState(size_t *total, size_t *logical, size_t *tofree, float *level) {
    size_t mem_reported, mem_used, mem_tofree;

    /* Check if we are over the memory usage limit. If we are not, no need
     * to subtract the slaves output buffers. We can just return ASAP. */
    mem_reported = zmalloc_used_memory();
    if (total) *total = mem_reported;

    /* We may return ASAP if there is no need to compute the level. */
    int return_ok_asap = !server.maxmemory || mem_reported <= server.maxmemory;
    if (return_ok_asap && !level) return C_OK;
    ...
```

zmalloc_used_memory이 사용되는 것을 알 수 있다! 그리고 여기서 얻은 값을 토대로 eviction 작업을 해야할지 말아야할 지를 결정한다.

## Conclusion
redis의 eviction 처리는 used_memory 에 의해 이루어지는 것을 확인할 수 있었다. 또한, used_memory_rss를 출력하기 위한 비용이 꽤 큰 관계로, `INFO` 커맨드에 의한 호출시마다 출력되지는 않고, serverCron에 의해 주기적으로 수집된 값을 표기한다는 것도 알 수 있었다.