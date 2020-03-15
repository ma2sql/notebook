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

*참고: 소스 코드는 4.0.14를 기준으로 분석한다.*

### 리플리카(슬레이브)에서의 CLUSTER FAILOVER 커맨드 실행

우선, `CLUSTER FAILOVER` 에 대한 처리가 어디서 시작되는지 확인해보자.
*https://github.com/antirez/redis/blob/4.0.14/src/cluster.c#L4584*
```c
void clusterCommand(client *c) {
    if (server.cluster_enabled == 0) {
        addReplyError(c,"This instance has cluster support disabled");
        return;
    }
...
        if (takeover) {
            /* A takeover does not perform any initial check. It just
             * generates a new configuration epoch for this node without
             * consensus, claims the master's slots, and broadcast the new
             * configuration. */
            serverLog(LL_WARNING,"Taking over the master (user request).");
            clusterBumpConfigEpochWithoutConsensus();
            clusterFailoverReplaceYourMaster();
        } else if (force) {
            /* If this is a forced failover, we don't need to talk with our
             * master to agree about the offset. We just failover taking over
             * it without coordination. */
            serverLog(LL_WARNING,"Forced failover user request accepted.");
            server.cluster->mf_can_start = 1;
        } else {
            serverLog(LL_WARNING,"Manual failover user request accepted.");
            clusterSendMFStart(myself->slaveof);
        }

```
`CLUSTER FAILOVER` 커맨드는 `cluster.c`의 `clusterCommand` 함수에서 처리되고 있으며, `FORCE|TAKEOVER` 등의 옵션이 없다면, `clusterSendMFStart (cluster.c)` 함수를 `myself->slaveof`(마스터) 인자값과 함께 호출하도록 되어있다. 그리고 서버 로그에는 *"Manual failover user request accepted."* 메시지가 출력된다.

*https://github.com/antirez/redis/blob/4.0.14/src/cluster.c#L2617*
```c
/* Send a MFSTART message to the specified node. */
void clusterSendMFStart(clusterNode *node) {
    unsigned char buf[sizeof(clusterMsg)];
    clusterMsg *hdr = (clusterMsg*) buf;
    uint32_t totlen;

    if (!node->link) return;
    clusterBuildMessageHdr(hdr,CLUSTERMSG_TYPE_MFSTART);
    totlen = sizeof(clusterMsg)-sizeof(union clusterMsgData);
    hdr->totlen = htonl(totlen);
    clusterSendMessage(node->link,buf,totlen);
}
```

`clusterSendMFStart` 함수 내에서는 `CLUSTERMSG_TYPE_MFSTART` 플래그를 이용하여 메시지 헤더를 만든 다음, `clusterSendMessage` 를 호출한다. 역시 인자로 전달받은 `myself->slaveof`, 즉 마스터 노드로 메시지가 전송된다.

### 마스터 노드의 PAUSE 처리

*https://github.com/antirez/redis/blob/4.0.14/src/cluster.c#L2046*
**client.c**
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
        serverLog(LL_WARNING,"Manual failover requested by slave %.40s.",
            sender->name);
        ...
```
마스터 노드에서는 리플리카 노드로부터 Manual Failover에 대한 메시지를 전달받아, 필요한 처리를 수행한다. 먼저, `resetManualFailover`를 호출하여, 메뉴얼 페일오버를 처리하는데 필요한 여러 변수를 초기화시킨다(mf_end, mf_slave  등등). 그리고 현재 시간을 기준으로 `CLUSTER_MF_TIMEOUT(5초)`만큼의 시간을 더해, 페일오버에 대한 타임아웃을 설정한다. 그리고 메시지를 보낸 노드를 신규 마스터 (mf_slave)로 지정한다. 이 과정을 마치고 난 이후에, `pauseClients`를 호출하여, 클라이언트로부터의 신규 커맨드의 발행을 막는다. `CLUSTER_MF_TIMEOUT`의 2배만큼 멈추므로 대략 10초간 신규 커맨드를 멈추게 된다. 마지막으로 *"Manual failover requested by slave (slave node ID)."* 메시지를 출력한다.

### 마스터 노드의 리플리케이션 오프셋 전송

*https://github.com/antirez/redis/blob/4.0.14/src/cluster.c#L3451*
```c
/* This is executed 10 times every second */
void clusterCron(void) {
...
        /* If we are a master and one of the slaves requested a manual
         * failover, ping it continuously. */
        if (server.cluster->mf_end &&
            nodeIsMaster(myself) &&
            server.cluster->mf_slave == node &&
            node->link)
        {
            clusterSendPing(node->link, CLUSTERMSG_TYPE_PING);
            continue;
        }
```
Pause 이후, 마스터와 리플리카 사이의 동기화 기준이 되는 포인트를 어디서 획득하고, 어떻게 전송하게 될까? 리플리카로 이러한 정보를 전달하는 것은, `clusterCron` 에서 처리하게 된다. `mf_end`와 `mf_slave`가 존재하면, `clusterSendPing` 함수를 호출하여, 신규 마스터가 될 리플리카로 메시지를 전송하게 된다. 과연 이 메시지에는 리플리케이션 오프셋 정보가 포함될까?

```c
/* Send a PING or PONG packet to the specified node, making sure to add enough
 * gossip informations. */
void clusterSendPing(clusterLink *link, int type) {
    unsigned char *buf;
    clusterMsg *hdr;
...
    /* Populate the header. */
    if (link->node && type == CLUSTERMSG_TYPE_PING)
        link->node->ping_sent = mstime();
    clusterBuildMessageHdr(hdr,type);
...
    /* Ready to send... fix the totlen fiend and queue the message in the
     * output buffer. */
    totlen = sizeof(clusterMsg)-sizeof(union clusterMsgData);
    totlen += (sizeof(clusterMsgDataGossip)*gossipcount);
    hdr->count = htons(gossipcount);
    hdr->totlen = htonl(totlen);
    clusterSendMessage(link,buf,totlen);
    zfree(buf);
```

오프셋 관련 계산이라던지, 무언가 힌트가 될만한 내용은 보이지 않는다. 다만, 리플리카가 `CLUSTER FAILOVER` 에 대한 명령을 처리하며 마스터로 메시지를 보내기위해 `clusterBuildMessageHdr`함수로 메시지 헤더를 생성하고, `clusterSendMessage` 함수로 최종적으로 메시지를 보낸 것 처럼, 이 함수 내에서도 동일한 함수가 목격된다.

```c
/* Build the message header. hdr must point to a buffer at least
 * sizeof(clusterMsg) in bytes. */
void clusterBuildMessageHdr(clusterMsg *hdr, int type) {
    int totlen = 0;
    uint64_t offset;
    clusterNode *master;
...
    /* Set the replication offset. */
    if (nodeIsSlave(myself))
        offset = replicationGetSlaveOffset();
    else
        offset = server.master_repl_offset;
    hdr->offset = htonu64(offset);

    /* Set the message flags. */
    if (nodeIsMaster(myself) && server.cluster->mf_end)
        hdr->mflags[0] |= CLUSTERMSG_FLAG0_PAUSED;
```

이곳에서 우리가 원하는 정보를 확인할 수가 있다. 먼저, 명령을 처리하는 자기 자신이 마스터 노드라면 `offset`정보에 `server.master_repl_offset` 정보를 담는다. 그리고 자신이 마스터이고, `mf_end`값이 존재한다면,  `CLUSTERMSG_FLAG0_PAUSED` 플래그를 설정한다. 즉, 현재 마스터 노드 자신이 Paused라는 것과 자신의 리플리케이션 오프셋 정보를 메시지 헤더에 설정하는 처리가 이루어지는 것이고, 이 정보가 신규 마스터가 될 리플리카 노드로 전달되는 것이다.

### 리플리카의 데이터 동기화

*https://github.com/antirez/redis/blob/4.0.14/src/cluster.c#L1707*
```c
/* When this function is called, there is a packet to process starting
 * at node->rcvbuf. Releasing the buffer is up to the caller, so this
 * function should just handle the higher level stuff of processing the
 * packet, modifying the cluster state if needed.
 *
 * The function returns 1 if the link is still valid after the packet
 * was processed, otherwise 0 if the link was freed since the packet
 * processing lead to some inconsistency error (for instance a PONG
 * received from the wrong sender ID). */
int clusterProcessPacket(clusterLink *link) {
...
        if (server.cluster->mf_end &&
            nodeIsSlave(myself) &&
            myself->slaveof == sender &&
            hdr->mflags[0] & CLUSTERMSG_FLAG0_PAUSED &&
            server.cluster->mf_master_offset == 0)
        {
            server.cluster->mf_master_offset = sender->repl_offset;
            serverLog(LL_WARNING,
                "Received replication offset for paused "
                "master manual failover: %lld",
                server.cluster->mf_master_offset);
        }
```
마스터가 보내준 메시지의 처리는 `clusterProcessPacket`함수에서 처리하게 된다. `CLUSTERMSG_FLAG0_PAUSED` 플래그를 확인해서 마스터가 정상적으로 Pause를 처리했는지, 그리고 `sender->repl_offset`을 확인하고 값이 있다면 `mf_master_offset`에 설정한다. 이 값이 마스터/리플리카 간의 데이터 동기화의 기준이 된다. 그렇다면 어느 부분에서 리플리케이션 오프셋 값을 비교하고 페일오버의 다음 단계로 넘어갈 수 있을까? 해답은 `clusterCron`에 존재한다.

*https://github.com/antirez/redis/blob/4.0.14/src/cluster.c#L3491*
```c
/* This is executed 10 times every second */
void clusterCron(void) {
...
    /* Abourt a manual failover if the timeout is reached. */
    manualFailoverCheckTimeout();

    if (nodeIsSlave(myself)) {
        clusterHandleManualFailover();
        clusterHandleSlaveFailover();
        /* If there are orphaned slaves, and we are a slave among the masters
         * with the max number of non-failing slaves, consider migrating to
         * the orphaned masters. Note that it does not make sense to try
         * a migration if there is no master with at least *two* working
         * slaves. */
        if (orphaned_masters && max_slaves >= 2 && this_slaves == max_slaves)
            clusterHandleSlaveMigration(max_slaves);
    }
```
`clusterCron`가 호출될 때마다, `clusterHandleManualFailover`나 `clusterHandleSlaveFailover` 함수는 호출되고, 실제로 페일오버가 필요하면 그에 맞는 처리가 수행되는 형태다. 즉, 일이 있으나 없으나 매번 함수가 호출되고 일이 없으면 그대로 무시, 있으면 필요한 처리를 수행하는 형태이다. 언급한대로 `clusterHandleManualFailover`가 호출되는 것을 확인할 수 있다.

*https://github.com/antirez/redis/blob/4.0.14/src/cluster.c#L3206*
```c
/* This function is called from the cluster cron function in order to go
 * forward with a manual failover state machine. */
void clusterHandleManualFailover(void) {
    /* Return ASAP if no manual failover is in progress. */
    if (server.cluster->mf_end == 0) return;

    /* If mf_can_start is non-zero, the failover was already triggered so the
     * next steps are performed by clusterHandleSlaveFailover(). */
    if (server.cluster->mf_can_start) return;

    if (server.cluster->mf_master_offset == 0) return; /* Wait for offset... */

    if (server.cluster->mf_master_offset == replicationGetSlaveOffset()) {
        /* Our replication offset matches the master replication offset
         * announced after clients were paused. We can start the failover. */
        server.cluster->mf_can_start = 1;
        serverLog(LL_WARNING,
            "All master replication stream processed, "
            "manual failover can start.");
    }
}
```
바로 이곳이 우리가 원하는 목적지이다. `mf_end`값이 존재하면 메뉴얼 페일오버가 진행되는 것으로 판단하고 본격적으로 데이터 동기화를 여부를 확인하고 다음 단계로 넘어가기 위해서, `mf_master_offset`값과 `replicationGetSlaveOffset`의 함수 호출 값을 비교한다. `replicationGetSlaveOffset`함수는 `server.master->reploff` 값을 반환하고, 값이 갱신된다면 계속해서 다른 값을 반환할 것이다. 즉, 두 값이 일치하는 순간 데이터 동기화가 완료되었다고 판단하며, 다음과 같은 메시지를 출력한다. *"All master replication stream processed, "manual failover can start.* 그리고 본격적인 페일오버 처리에 돌입할 수 있도록 `mf_can_start`값을 1로 지정한다.


Manual Failover가 시작되면 처리되는 여러 함수 중, `pauseClients()` 함수를 확인할 수 있다. 그리고 이 함수는 networking.c 에 존재한다.


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