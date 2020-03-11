Replication
===

레디스 리플리케이션(레디스 클러스터나 센티털에 의해 추가적인 계층에서 제공되는 고가용성 기능을 제외하는)의 기본에는 매우 단순하게 사용하고 구성할 수 있는 *리더 팔로워(leader follwer)* (master-slave)라는 리플리케이션이 있다: 그것은 리플리카 레디스 인스턴스가 마스터 인스턴스의 완전한 복제본이 되는 것이다. 리플리카는 연결이 깨질때마다, 자동적으로 마스터로의 재연결하고, 마스터에 무슨 일이 있던지에 관계없이 완전한 복제본이 되기 위해 시도한다.

이 시스템은 세 가지의 주요 메커니즘을 이용해서 작동한다:

1. 마스터와 리플리카 인스턴스가 무사히 커넥션을 맺고 있을 때, 마스터는 업데이트된 리플리카를 유지하려고 커맨드의 스트림을 리플리카로 전송한다. 이는 클라이언트 쓰기(write) 오퍼레이션, 키의 만료, 축출, 그 외의 마스터 데이터 셋을 변경시키는 액션 등, 마스터 측에서 발생하는 데이터 셋에 대한 영향을 복제하기 위해서이다.
2. 네트워크 이슈나 마스터나 리플리에서 감지된 타임 아웃 등등으로 마스터와 리플리카 사이의 연결이 깨질 때, 리플리카는 재연결과 부분 재동기화(partial resynchronization)를 시도한다: 이것은 단순히 연결이 끊긴 시간 동안에 잃어버린 커맨드의 스트림 일부만을 얻으려고 시도하는 것을 의미한다.
3. 부분 재동기화가 가능하지 않을 때, 리플리카는 전체 재동기화를 요청한다. 이것은 마스터가 자신의 데이터 전체에 대한 스냅샷을 작성하고, 그것을 리플리카로 전송할 필요가 있으며, 그리고 나서 데이터 셋이 변경될 때마다 커맨드의 스트림을 계속 전송하는 등의 좀 더 복잡한 절차가 포함된다.

레디스는 적은 지연 시간과 높은 성능의 비동기 리플리케이션을 기본적으로 사용하고, 이것은 대부분의 레디스 사용 케이스에서 일반적인 복제 모드이다. 그러나 레디스 리플리카는 마스터로부터 주기적으로 전달받은 데이터의 양에 대해서 비동기적으로 응답한다. 그래서 마스터는 리플리카에 의해 처리된 커맨드에 대해서 매번 대기하지 않지만, 필요하면 무슨 리플리카가 이미 무슨 커맨드를 처리를 했는지를 알 수 있다. 이것으로 선택적인 동기 복제가 가능하다.

Synchronous replication of certain data can be requested by the clients using the `WAIT` command. However `WAIT` is only able to ensure that there are the specified number of acknowledged copies in the other Redis instances, it does not turn a set of Redis instances into a CP system with strong consistency: acknowledged writes can still be lost during a failover, depending on the exact configuration of the Redis persistence. However with `WAIT` the probability of losing a write after a failure event is greatly reduced to certain hard to trigger failure modes.

특정 데이터의 동기 복제는 클라이언트로가 `WAIT`커맨드가 요청함으로써 가능하다. 그러나 `WAIT`는 다른 레디스 인스턴스에서 응답이 오직 지정된 수 만큼 있었다는 것만을 보장하며, CP시스템으로써 강한 일관성을 제공해주지는 않는다. 응답된 쓰기는 여전히 페일오버 서점에 손실될 수 있으며, 레디스 영속성의 관련된 설정에 달려있다. 그러나 `WAIT`커맨드로 실패 이벤트 이후의 데이터 손실 가능성을 매우 줄일 수 있다.


You could check the Sentinel or Redis Cluster documentation for more information
about high availability and failover. The rest of this document mainly describe the basic characteristics of Redis basic replication.

The following are some very important facts about Redis replication:

* Redis uses asynchronous replication, with asynchronous replica-to-master acknowledges of the amount of data processed.
* A master can have multiple replicas.
* Replicas are able to accept connections from other replicas. Aside from connecting a number of replicas to the same master, replicas can also be connected to other replicas in a cascading-like structure. Since Redis 4.0, all the sub-replicas will receive exactly the same replication stream from the master.
* Redis replication is non-blocking on the master side. This means that the master will continue to handle queries when one or more replicas perform the initial synchronization or a partial resynchronization.
* Replication is also largely non-blocking on the replica side. While the replica is performing the initial synchronization, it can handle queries using the old version of the dataset, assuming you configured Redis to do so in redis.conf.  Otherwise, you can configure Redis replicas to return an error to clients if the replication stream is down. However, after the initial sync, the old dataset must be deleted and the new one must be loaded. The replica will block incoming connections during this brief window (that can be as long as many seconds for very large datasets). Since Redis 4.0 it is possible to configure Redis so that the deletion of the old data set happens in a different thread, however loading the new initial dataset will still happen in the main thread and block the replica.
* Replication can be used both for scalability, in order to have multiple replicas for read-only queries (for example, slow O(N) operations can be offloaded to replicas), or simply for improving data safety and high availability.
* It is possible to use replication to avoid the cost of having the master writing the full dataset to disk: a typical technique involves configuring your master `redis.conf` to avoid persisting to disk at all, then connect a replica configured to save from time to time, or with AOF enabled. However this setup must be handled with care, since a restarting master will start with an empty dataset: if the replica tries to synchronized with it, the replica will be emptied as well.

Safety of replication when master has persistence turned off
---

In setups where Redis replication is used, it is strongly advised to have persistence turned on in the master and in the replicas. When this is not possible, for example because of latency concerns due to very slow disks, instances should be configured to **avoid restarting automatically** after a reboot.

To better understand why masters with persistence turned off configured to auto restart are dangerous, check the following failure mode where data is wiped from the master and all its replicas:

1. We have a setup with node A acting as master, with persistence turned down, and nodes B and C replicating from node A.
2. Node A crashes, however it has some auto-restart system, that restarts the process. However since persistence is turned off, the node restarts with an empty data set.
3. Nodes B and C will replicate from node A, which is empty, so they'll effectively destroy their copy of the data.

When Redis Sentinel is used for high availability, also turning off persistence on the master, together with auto restart of the process, is dangerous. For example the master can restart fast enough for Sentinel to not detect a failure, so that the failure mode described above happens.

Every time data safety is important, and replication is used with master configured without persistence, auto restart of instances should be disabled.

How Redis replication works
---

Every Redis master has a replication ID: it is a large pseudo random string that marks a given story of the dataset. Each master also takes an offset that increments for every byte of replication stream that it is produced to be sent to replicas, in order to update the state of the replicas with the new changes modifying the dataset. The replication offset is incremented even if no replica is actually connected, so basically every given pair of:

    Replication ID, offset

Identifies an exact version of the dataset of a master.

When replicas connect to masters, they use the `PSYNC` command in order to send their old master replication ID and the offsets they processed so far. This way the master can send just the incremental part needed. However if there is not enough *backlog* in the master buffers, or if the replica is referring to an history (replication ID) which is no longer known, than a full resynchronization happens: in this case the replica will get a full copy of the dataset, from scratch.

This is how a full synchronization works in more details:

The master starts a background saving process in order to produce an RDB file. At the same time it starts to buffer all new write commands received from the clients. When the background saving is complete, the master transfers the database file to the replica, which saves it on disk, and then loads it into memory. The master will then send all buffered commands to the replica. This is done as a stream of commands and is in the same format of the Redis protocol itself.

You can try it yourself via telnet. Connect to the Redis port while the server is doing some work and issue the `SYNC` command. You'll see a bulk transfer and then every command received by the master will be re-issued in the telnet session. Actually `SYNC` is an old protocol no longer used by newer Redis instances, but is still there for backward compatibility: it does not allow partial resynchronizations, so now `PSYNC` is used instead.

As already said, replicas are able to automatically reconnect when the master-replica link goes down for some reason. If the master receives multiple concurrent replica synchronization requests, it performs a single background save in order to serve all of them.

Replication ID explained
---

이전 섹션에서 우리는 두 인스턴스가 동일한 리플리케이션 ID와 리플리케이션 오프셋을 가지고 있다면, 그 둘은 완전히 동일한 데이터라고 이야기했다. 하지만 정확히 리플리케이션 ID가 무엇인지? 그리고 왜 인스턴스가 실제 메인 ID와 세컨더리 ID, 2개의 리플리케이션 ID를 가지고 있는지를 이해하는 것에 유용하다.

리플리케이션 ID는 기본적으로 지정된 데이터 셋의 *이력(history)*을 표시한다. 인스턴스가 마스터로 재시작하거나, 리플리카가 마스터로 승력될 때마다, 이 인스턴스에 대해서는 새로운 리플리케이션 ID가 생성된다. 마스터로 연결된 리플리카들은 핸드쉐이크 이후에 마스터의 리플리케이션 ID를 상속할 것이다. 그래서 동일한 ID를 가진 두 인스턴스는 잠재적으로 다른 시간에 동일한 데이터를 가지고 있다는 사실에 의해 연관된다.  논리적인 시간으로 작용하는 오프셋이다. 가장 많이 업데이트된 데이터 셋을 가지는 특정 이력(리플리케이션 ID)을 알기 위한 논리적인 시간으로 작동하는 오프셋이다.

예를 들어, 인스턴스 A와 B, 두 개의 인스턴스가 같은 리플리케이션 ID를 가지고 있지만, 하나는 오프셋이 1000, 그리고 다른 하나는 오프셋이 1023이라고 할 때, 첫 번째는 데이터 셋에 적용된 특정 커맨드가 없다는 것을 의미한다. 또한 A가 몇 개의 커맨드를 적용함으로써 B와 정확히 동일한 상태가 될 수 있다는 것을 의미한다.

왜 레디스 인스턴스가 2개의 리플리케이션을 가지고 있는지에 대한 이유는 마스터로 승격되는 리플리카 때문이다. 페일오버 이후, 승격된 리플리카는 여전히 지난 리플리케이션 ID가 무엇인지 기억해야할 필요가 있는데, 그러한 리플리케이션 ID가 이전의 마스터의 것 중에 하나이기 때문이다. 이러한 방식으로, 다른 리플리카가 새로운 마스터와 동기화할 때, 오래된 마스터의 리플리케이션 ID를 이용해서 부분 재동기화를 시도한다. 이것은 예상한대로 동작하는데, 리플리카가 마스터로 승격될 때 세컨더리 ID를 메인 ID로 설정하고, ID 변경이 발생했을 때의 오프셋이 무엇인지를 기억하기 때문이다. 이 후, 새로운 히스토리가 시작되므로 새로운 랜덤 ID를 선택해서 사용한다. 새로운 리플리카들에 대한 연결을 처리할 때, 마스터는 리플리카들의 IDs와 오프셋을 현재의 ID와 세컨더리 ID (안전을 위해 지정된 오프셋까지)까지 일치시킨다. 즉, 이것은 페일오버 이후에 새롭게 승격된 마스터로 연결하려는 리플리카는 전체 동기화를 수행할 필요가 없다는 것을 의미한다.

이러한 경우에 왜 마스터로 승격된 리플리카가 페일오버 이후에 자신의 리플리케이션 ID를 변경해야하는지가 궁금할 것이다: 오래된 마스터는 여전히 마스터로 동작하고 있을 수 있는데, 왜냐하면 일부 네트워크 파티션 때문이다. 동일한 리플리케이션 ID를 유지하는 것은 동일한 ID와 동일한 오프셋을 가진 임의의 2개의 인스턴스는 동일한 데이터 셋을 가지고 있다는 사실(fact)을 위반하기 때문이다.

Diskless replication
---

Normally a full resynchronization requires creating an RDB file on disk, then reloading the same RDB from disk in order to feed the replicas with the data.

With slow disks this can be a very stressing operation for the master. Redis version 2.8.18 is the first version to have support for diskless replication. In this setup the child process directly sends the RDB over the wire to replicas, without using the disk as intermediate storage.

Configuration
---

To configure basic Redis replication is trivial: just add the following line to the replica configuration file:

    replicaof 192.168.1.1 6379

Of course you need to replace 192.168.1.1 6379 with your master IP address (or hostname) and port. Alternatively, you can call the `REPLICAOF` command and the master host will start a sync with the replica.

There are also a few parameters for tuning the replication backlog taken in memory by the master to perform the partial resynchronization. See the example `redis.conf` shipped with the Redis distribution for more information.

Diskless replication can be enabled using the `repl-diskless-sync` configuration parameter. The delay to start the transfer in order to wait for more replicas to arrive after the first one is controlled by the `repl-diskless-sync-delay` parameter. Please refer to the example `redis.conf` file in the Redis distribution for more details.

Read-only replica
---

Since Redis 2.6, replicas support a read-only mode that is enabled by default. This behavior is controlled by the `replica-read-only` option in the redis.conf file, and can be enabled and disabled at runtime using `CONFIG SET`.

Read-only replicas will reject all write commands, so that it is not possible to write to a replica because of a mistake. This does not mean that the feature is intended to expose a replica instance to the internet or more generally to a network where untrusted clients exist, because administrative commands like `DEBUG` or `CONFIG` are still enabled. However, security of read-only instances can be improved by disabling commands in redis.conf using the `rename-command` directive.

You may wonder why it is possible to revert the read-only setting and have replica instances that can be targeted by write operations. While those writes will be discarded if the replica and the master resynchronize or if the replica is restarted, there are a few legitimate use case for storing ephemeral data in writable replicas.

For example computing slow Set or Sorted set operations and storing them into local keys is an use case for writable replicas that was observed multiple times.

However note that **writable replicas before version 4.0 were incapable of expiring keys with a time to live set**. This means that if you use `EXPIRE` or other commands that set a maximum TTL for a key, the key will leak, and while you may no longer see it while accessing it with read commands, you will see it in the count of keys and it will still use memory. So in general mixing writable replicas (previous version 4.0) and keys with TTL is going to create issues.

Redis 4.0 RC3 and greater versions totally solve this problem and now writable replicas are able to evict keys with TTL as masters do, with the exceptions of keys written in DB numbers greater than 63 (but by default Redis instances only have 16 databases).

Also note that since Redis 4.0 replica writes are only local, and are not propagated to sub-replicas attached to the instance. Sub-replicas instead will always receive the replication stream identical to the one sent by the top-level master to the intermediate replicas. So for example in the following setup:

    A ---> B ---> C

Even if `B` is writable, C will not see `B` writes and will instead have identical dataset as the master instance `A`.

Setting a replica to authenticate to a master
---

If your master has a password via `requirepass`, it's trivial to configure the replica to use that password in all sync operations.

To do it on a running instance, use `redis-cli` and type:

    config set masterauth <password>

To set it permanently, add this to your config file:

    masterauth <password>

Allow writes only with N attached replicas
---

Starting with Redis 2.8, it is possible to configure a Redis master to accept write queries only if at least N replicas are currently connected to the master.

However, because Redis uses asynchronous replication it is not possible to ensure the replica actually received a given write, so there is always a window for data loss.

This is how the feature works:

* Redis replicas ping the master every second, acknowledging the amount of replication stream processed.
* Redis masters will remember the last time it received a ping from every replica.
* The user can configure a minimum number of replicas that have a lag not greater than a maximum number of seconds.

If there are at least N replicas, with a lag less than M seconds, then the write will be accepted.

You may think of it as a best effort data safety mechanism, where consistency is not ensured for a given write, but at least the time window for data loss is restricted to a given number of seconds. In general bound data loss is better than unbound one.

If the conditions are not met, the master will instead reply with an error and the write will not be accepted.

There are two configuration parameters for this feature:

* min-replicas-to-write `<number of replicas>`
* min-replicas-max-lag `<number of seconds>`

For more information, please check the example `redis.conf` file shipped with the Redis source distribution.

How Redis replication deals with expires on keys
---

Redis expires allow keys to have a limited time to live. Such a feature depends on the ability of an instance to count the time, however Redis replicas correctly replicate keys with expires, even when such keys are altered using Lua scripts.

To implement such a feature Redis cannot rely on the ability of the master and replica to have synchronized clocks, since this is a problem that cannot be solved and would result in race conditions and diverging data sets, so Redis uses three main techniques in order to make the replication of expired keys able to work:

1. Replicas don't expire keys, instead they wait for masters to expire the keys. When a master expires a key (or evict it because of LRU), it synthesizes a `DEL` command which is transmitted to all the replicas.
2. However because of master-driven expire, sometimes replicas may still have in memory keys that are already logically expired, since the master was not able to provide the `DEL` command in time. In order to deal with that the replica uses its logical clock in order to report that a key does not exist **only for read operations** that don't violate the consistency of the data set (as new commands from the master will arrive). In this way replicas avoid reporting logically expired keys are still existing. In practical terms, an HTML fragments cache that uses replicas to scale will avoid returning items that are already older than the desired time to live.
3. During Lua scripts executions no key expiries are performed. As a Lua script runs, conceptually the time in the master is frozen, so that a given key will either exist or not for all the time the script runs. This prevents keys expiring in the middle of a script, and is needed in order to send the same script to the replica in a way that is guaranteed to have the same effects in the data set.

Once a replica is promoted to a master it will start to expire keys independently, and will not require any help from its old master.

Configuring replication in Docker and NAT
---

When Docker, or other types of containers using port forwarding, or Network Address Translation is used, Redis replication needs some extra care, especially when using Redis Sentinel or other systems where the master `INFO` or `ROLE` commands output are scanned in order to discover replicas' addresses.

The problem is that the `ROLE` command, and the replication section of the `INFO` output, when issued into a master instance, will show replicas as having the IP address they use to connect to the master, which, in environments using NAT may be different compared to the logical address of the replica instance (the one that clients should use to connect to replicas).

Similarly the replicas will be listed with the listening port configured into `redis.conf`, that may be different than the forwarded port in case the port is remapped.

In order to fix both issues, it is possible, since Redis 3.2.2, to force a replica to announce an arbitrary pair of IP and port to the master.

The two configurations directives to use are:

    replica-announce-ip 5.5.5.5
    replica-announce-port 1234

And are documented in the example `redis.conf` of recent Redis distributions.

The INFO and ROLE command
---

There are two Redis commands that provide a lot of information on the current replication parameters of master and replica instances. One is `INFO`. If the command is called with the `replication` argument as `INFO replication` only information relevant to the replication are displayed. Another more computer-friendly command is `ROLE`, that provides the replication status of masters and replicas together with their replication offsets, list of connected replicas and so forth.

Partial resynchronizations after restarts and failovers
---

Since Redis 4.0, when an instance is promoted to master after a failover, it will be still able to perform a partial resynchronization with the replicas of the old master. To do so, the replica remembers the old replication ID and offset of its former master, so can provide part of the backlog to the connecting replicas even if they ask for the old replication ID.

However the new replication ID of the promoted replica will be different, since it constitutes a different history of the data set. For example, the master can return available and can continue accepting writes for some time, so using the same replication ID in the promoted replica would violate the rule that a of replication ID and offset pair identifies only a single data set.

Moreover, replicas - when powered off gently and restarted - are able to store in the `RDB` file the information needed in order to resynchronize with their master. This is useful in case of upgrades. When this is needed, it is better to use the `SHUTDOWN` command in order to perform a `save & quit` operation on the replica.

It is not possible to partially resynchronize a replica that restarted via the AOF file. However the instance may be turned to RDB persistence before shutting down it, than can be restarted, and finally AOF can be enabled again.
