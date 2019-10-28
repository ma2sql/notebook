---
tags: [redis]
---

## Manual Failover
*https://redis.io/commands/cluster-failover*

다음은 manual failover에 대한 절차이다.

1. The replica tells the master to stop processing queries from clients.
2. The master replies to the replica with the current replication offset.
3. The replica waits for the replication offset to match on its side, to make sure it processed all the data from the master before it continues.
4. The replica starts a failover, obtains a new configuration epoch from the majority of the masters, and broadcasts the new configuration.
5. The old master receives the configuration update: unblocks its clients and starts replying with redirection messages so that they'll continue the chat with the new master.

기존(old) 마스터의 쿼리 처리를 멈춘다(블로킹)고 되어있다. 이후 master-slave간의 동기화를 마치고, failover 를 통해 role 을 변경한 다음, old 마스터로 블로킹을 해제하고, 리다이렉션을 발생시킨다. 그렇다면 old 마스터의 쿼리는 어떠한 식으로 멈출 수 있을까? 또한, 이에 대해 레디스 클라이언트는 어떻게 반응하게 될까?

** client.c **
```c
    ...
    } else if (type == CLUSTERMSG_TYPE_MFSTART) {
        /* This message is acceptable only if I'm a master and the sender
         * is one of my slaves. */
        if (!sender || sender->slaveof != myself) return 1;
        /* Manual failover requested from slaves. Initialize the state
         * accordingly. */
        resetManualFailover();
        server.cluster->mf_end = mstime() + CLUSTER_MF_TIMEOUT;
        server.cluster->mf_slave = sender;
        pauseClients(mstime()+(CLUSTER_MF_TIMEOUT*2));
        serverLog(LL_WARNING,"Manual failover requested by replica %.40s.",
            sender->name);
        ...
```

Manual Failover가 시작되면 처리되는 여러 함수 중, `pauseClients()` 함수를 확인할 수 있다. 그리고 이 함수는 network.c에  존재한다.


```c
void pauseClients(mstime_t end) {
    if (!server.clients_paused || end > server.clients_pause_end_time)
        server.clients_pause_end_time = end;
    server.clients_paused = 1;
}

/* Return non-zero if clients are currently paused. As a side effect the
 * function checks if the pause time was reached and clear it. */
int clientsArePaused(void) {
    if (server.clients_paused &&
        server.clients_pause_end_time < server.mstime)
    {
        listNode *ln;
        listIter li;
        client *c;

        server.clients_paused = 0;

        /* Put all the clients in the unblocked clients queue in order to
         * force the re-processing of the input buffer if any. */
        listRewind(server.clients,&li);
        while ((ln = listNext(&li)) != NULL) {
            c = listNodeValue(ln);

            /* Don't touch slaves and blocked clients.
             * The latter pending requests will be processed when unblocked. */
            if (c->flags & (CLIENT_SLAVE|CLIENT_BLOCKED)) continue;
            queueClientForReprocessing(c);
        }
    }
    return server.clients_paused;
}
...

void processInputBuffer(client *c) {
    /* Keep processing while there is something in the input buffer */
    while(c->qb_pos < sdslen(c->querybuf)) {
        /* Return if clients are paused. */
        if (!(c->flags & CLIENT_SLAVE) && clientsArePaused()) break;

```

`pauseClients`는 단순히 전달받은 파라미터로 server.clients_pause_end_time 값을 변경하고, server.clients_paused를 1로 변경시킨다. 즉, 지금 pause된 상태인지? 어느 시점까지 pause를 지속시킬 것인가? 를 지정하는 것이다. 그리고 이 두 변수들은 주로 `clientsArePaused` 이 곳에서 사용된다. 이 함수는 클라이언트가 지금 pause 상태인지를 확인하고 그에 따른 적절한 처리를 한 이후, server.clients_paused 값을 반환한다. pause가 만료된 상태라면 server.clients_paused를 0으로 초기화하기도 한다.

쿼리 버퍼를 처리하는 `processInputBuffer`에서 `clientsArePaused`를 호출하고 pause 상태이면 바로 루프를 빠져나와 쿼리 처리를 보류시킨다.

여기까지 정리하면, Cluster의 Manual Failover에 의해 서버는 전역적으로 pause 상태에 돌입하고 (대략 10초), 쿼리 버퍼의 처리는 보류되게 된다. 그렇다면 pause 는 언제 해제되는 것일까? 자연히 server.clients_pause_end_time 만료 시간까지 기다려야 하는 것일까? 그렇게 되면 클라이언트는 대략 10초간 아무런 응답을 받지 못하며, 페일오버 이후의 MOVED 리다이렉션도 처리하지 못할텐데?

```c
...
   } else if (type == CLUSTERMSG_TYPE_UPDATE) {
        clusterNode *n; /* The node the update is about. */
        uint64_t reportedConfigEpoch =
                    ntohu64(hdr->data.update.nodecfg.configEpoch);

        if (!sender) return 1;  /* We don't know the sender. */
        n = clusterLookupNode(hdr->data.update.nodecfg.nodename);
        if (!n) return 1;   /* We don't know the reported node. */
        if (n->configEpoch >= reportedConfigEpoch) return 1; /* Nothing new. */

        /* If in our current config the node is a slave, set it as a master. */
        if (nodeIsSlave(n)) clusterSetNodeAsMaster(n);

        /* Update the node's configEpoch. */
        n->configEpoch = reportedConfigEpoch;
        clusterDoBeforeSleep(CLUSTER_TODO_SAVE_CONFIG|
                             CLUSTER_TODO_FSYNC_CONFIG);

        /* Check the bitmap of served slots and update our
         * config accordingly. */
        clusterUpdateSlotsConfigWith(n,reportedConfigEpoch,
            hdr->data.update.nodecfg.slots);
    } else if (type == CLUSTERMSG_TYPE_MODULE) {
...

/* Reset the manual failover state. This works for both masters and slavesa
 * as all the state about manual failover is cleared.
 *
 * The function can be used both to initialize the manual failover state at
 * startup or to abort a manual failover in progress. */
void resetManualFailover(void) {
    if (server.cluster->mf_end && clientsArePaused()) {
        server.clients_pause_end_time = 0;
        clientsArePaused(); /* Just use the side effect of the function. */
    }
    server.cluster->mf_end = 0; /* No manual failover in progress. */
    server.cluster->mf_can_start = 0;
    server.cluster->mf_slave = NULL;
    server.cluster->mf_master_offset = 0;
}
```

클러스터의 failover 이후, UPDATE 메시지를 전체 노드는 이를 수신하게 될 것이고, old 마스터 또한 마찬가지이다. 이 메시지를 수신하면 `clusterUpdateSlotsConfigWith` 함수를 호출하게 되는데, 내부적으로는 `resetManualFailover` 함수도 호출하게 된다. 바로 여기서 clientsArePaused를 호출하고, 아직 pause 상태라면 server.clients_pause_end_time를 0으로 초기화하여 pause를 해제시킨다.

결국, old 마스터에 대한 pause는 만료 시간까지 기다리지 않고, FAILOVER 이후 수신하게 되는 UPDATE message에 의해 pause가 풀리게 되는 것이다. CLUSTER FAILOVER 절차가 빠르게 마무리 될수록, UPDATE message가 빠르게 전파될수록 pause 상태는 짧아지게 될 것이다. 신규 마스터의 승격은 PSYNC시간, 즉 데이터 동기화가 아니라 단순히 롤 변경/부여이므로 페일오버 완료 후 1초 내에는 pause가 풀리게 될 것이다.