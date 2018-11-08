# Good slave conditions

### Redis Sentinel에서 프로모션이 가능한 `GOOD SLAVE`가 되는 조건
1. 슬레이브의 상태에 다음이 포함되지 않을 때: S_DOWN, O_DOWN, DISCONNECTED
2. 슬레이브가 마지막으로 PING에 응답한 `PING period * 5` 이내일 때
  - SENTINEL_PING_PERIOD(1000ms) * 5 = **5000** ms
3. 슬레이브에 대한 최신의 INFO 갱신 시간이 `INFO refresh period * 3` 이내일 때
  - SENTINEL_INFO_PERIOD(10000ms) * 3 = **30000** ms
4. master_link_down_time값이 제한값을 초과하는 경우
  - 제한값: (now - master->s_down_since_time) + (master->down_after_period * 10)
    - SDOWN이 된 시점부터 down_after_period*10 시간까지가 제한값
  - sdown이후 10초가 지나고, down_after_period가 10초라면, **(now_timestamp() - 10) + (10*10)**
5. slave_priority가 0으로 설정되어 있지 않은 경우

*여기서 적절한 슬레이브를 찾지 못한다면, 다음과 같은 에러가 발생한다.*
- -NOGOODSLAVE No suitable slave to promote (in sentinel interactive client)
- -failover-abort-no-good-slave (in sentienl damon log)

```
/*
* 1) None of the following conditions: S_DOWN, O_DOWN, DISCONNECTED.
* 2) Last time the slave replied to ping no more than 5 times the PING period.
* 3) info_refresh not older than 3 times the INFO refresh period.
* 4) master_link_down_time no more than:
*     (now - master->s_down_since_time) + (master->down_after_period * 10).
*    Basically since the master is down from our POV, the slave reports
*    to be disconnected no more than 10 times the configured down-after-period.
*    This is pretty much black magic but the idea is, the master was not
*    available so the slave may be lagging, but not over a certain time.
*    Anyway we'll select the best slave according to replication offset.
* 5) Slave priority can't be zero, otherwise the slave is discarded.
*/
```

```c
sentinelRedisInstance *sentinelSelectSlave(sentinelRedisInstance *master) {
    sentinelRedisInstance **instance =
        zmalloc(sizeof(instance[0])*dictSize(master->slaves));
    sentinelRedisInstance *selected = NULL;
    int instances = 0;
    dictIterator *di;
    dictEntry *de;
    mstime_t max_master_down_time = 0;

    // master_link_down_time 시간과 비교할 값(max_master_down_time) 계산
    if (master->flags & SRI_S_DOWN)
        // SDOWN된 시점 (now - s_down_since_time)
        max_master_down_time += mstime() - master->s_down_since_time;
        // (down_after_period * 10)
        max_master_down_time += master->down_after_period * 10;

    di = dictGetIterator(master->slaves);
    while((de = dictNext(di)) != NULL) {
        sentinelRedisInstance *slave = dictGetVal(de);
        mstime_t info_validity_time;

        // 다음 상태의 슬레이브는 프로모션 대상에서 제외: S_DOWN, O_DOWN, DISCONNECTED
        if (slave->flags & (SRI_S_DOWN|SRI_O_DOWN|SRI_DISCONNECTED)) continue;
        // ping 응답 시간이 SENTINEL_PING_PERIOD*5 보다 크면 제외
        if (mstime() - slave->last_avail_time > SENTINEL_PING_PERIOD*5) continue;
        // slave_priority가 0면 제외
        if (slave->slave_priority == 0) continue;

        /* If the master is in SDOWN state we get INFO for slaves every second.
         * Otherwise we get it with the usual period so we need to account for
         * a larger delay. */
        // info_validity_time 값 구하기
        if (master->flags & SRI_S_DOWN)
            info_validity_time = SENTINEL_PING_PERIOD*5;
        else
            info_validity_time = SENTINEL_INFO_PERIOD*3;
        // info값을 갱신한 것이 유효한 시간 범위 밖이라면 제외
        if (mstime() - slave->info_refresh > info_validity_time) continue;
        // master와 연결이 끊긴 시점이, 유효한 시간 제한 값 이상이라면 제외
        if (slave->master_link_down_time > max_master_down_time) continue;
        instance[instances++] = slave;
    }
    dictReleaseIterator(di);
    if (instances) {
        qsort(instance,instances,sizeof(sentinelRedisInstance*),
            compareSlavesForPromotion);
        selected = instance[0];
    }
    zfree(instance);
    return selected;
}
```
