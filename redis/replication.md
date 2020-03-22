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

레디스 리플리케이션이 사용되는 설정에서는 영속성(persistence)을 마스터와 리플리카에서 켜는 것이 매우 권장된다. 예를 들어 매우 느린 디스크 때문에 응답 시간(latency)이 우려되거나 하는 등의 이유로 이렇게 할 수 없을 때, 인스턴스는 서버의 재기동 이후에 **자등으로 재시작되지 않도록** 구성이 되어야 한다.

왜 영속성(persistence)을 비활성화한 마스터가 자동으로 재시작하도록 구성하는 것이 위험한지에 대해서 더 잘 이해하기 위해서는, 마스터와 모든 리플리카에서 데이터가 삭제되어버릴 수 있는 실패 케이스를 체크해야한다:

1. 노드 A를 영속성이 비활성화된 마스터로, 그리고 노드 B와 C가 A를 복제하도록 셋업한다. 
2. 노드 A는 크래시되지만, 자동으로 재시작하는 시스템을 가지고 있어, 레디스 프로세스는 결국 재시작될 것이다. 하지만 영속성이 비활성화되어 있기 때문에, 마스터 노드는 빈 데이터 셋으로 재시작한다.
3. 노드 B와 C는 빈 데이터 셋을 가진 노드 A로부터 복제할 것이고, 그래서 사실상 데이터 셋의 복제본은 모두 소실될 것이다.

고가용성(High Availability)을 위해 레디스 센티널을 사용할 때, 자동으로 프로세스를 재시작하는 시스템을 가진 마스터에서 영속성을 비활성화하는 것 또한 위험하다. 예를 들어, 마스터는 센티널이 실패를 감지하지 못할만큼 빠르게 재시작될 수 있고, 따라서 위에서 설명한 실패 케이스가 발생한다.

데이터 안전성이 중요하고, 영속성 없이 구성된 마스터가 리플리케이션에 사용될 때에는, 인스턴스의 자동 재시작은 반드시 비활성화되어야 한다.

How Redis replication works
---

모든 레디스 마스터는 리플리케이션 ID를 가진다: 이것은 큰 의사(pseudo) 랜덤 문자열로, 지정된 데이터 셋의 이력을 표시한다. 또한 각 마스터는 오프셋을 취하는데, 이 오프셋은 리플리카로 전송하기 위해서 생성되는 것으로 리플리케이션 스트림의 모든 바이트를 증가시키는데, 이는 데이터 셋을 수정하는 새로운 변경사항으로 리플리케이션의 상태를 업데이트하기 위해서다. 리플리케이션 오프셋은 심지어 연결된 리플리카가 없어도 증가되는데, 그렇기 때문에 기본적으로 주어진 오프셋의 한 쌍은:

    Replication ID, offset

마스터 데이터 셋의 정확한 버전을 식별한다.

리플리카가 마스터로 접속할 때, 이전 마스터의 리플리케이션 ID와 지금까지 처리한 오프셋을 전송하기 위해 `PSYNC` 커맨드를 사용한다. 이렇게 해서 마스터는 필요한만큼의 증가분만 보낼 수 있다. 그러나 마스터 버퍼 내에 충분한 양의 *백로그(backlog)* 가 존재하지 않거나, 또는 만약 리플리카가 더 이상 알려지지 않은 히스토리(리플리케이션 ID)를 참조하고 있을 때, 그렇게 되면 맨 처음부터 전체 재동기화(full resynchronization)가 발생한다.

이것은 어떻게 전체 동기화가 작동하는지에 대한 좀 더 상세한 내용이다:

마스터는 RDB 파일을 생성하기 위해서 백그라운드 세이빙(saving) 프로세스를 시작한다. 동시에 클라이언트로부터 전달받은 모든 새로운 쓰기 커맨드를 버퍼에 담기 시작한다. 백그라운드 세이빙(saving)이 완료되면, 마스터는 데이터셋 파일을 리플리카로 전송하고, 리플리카는 그것을 디스크에 저장하고, 그리고 메모리로 불러들인다(load). 그러면 마스터는 모든 버퍼된 커맨드를 리플리카로 보낼 것이다. 이것은 커맨드의 스트림으로써 수행되고, 레디스 프로토콜 자체와 동일한 포맷이다.

당신은 텔넷을 이용해서 직접 시도해볼 수 잇다. 서버가 어떤 작업을 하고 있는 동안, 레디스 포트로 접근해서 `SYNC` 커맨드를 발급한다. 그러면 대량으로 전송이 시작되는 것을 볼 수 있고, 마스터가 받은 모든 커맨드가 텔넷 세션에서 다시 발행될 것이다. 실제로 `SYNC`는 오래된 프로토콜로 신규 레디스 인스턴스에서는 더 이상 사용되지 않지만, 하위 호환성을 위해서 여전히 존재한다: 부분 재동기화는 가능하지 않기 때문에, 현재는 `PSYNC`가 대신 사용된다.

이미 언급한대로, 마스터-리플리카 연결이 어떠한 이유로 중단되었을 때, 리플리카들은 자동으로 재연결을 할 수 있다. 만약, 마스터가 동시에 여러 리플리카의 동기화 요청을 받게 된다면, 마스터는 모든 요청을 처리하기 위해 단일 백그라운드 세이브를 수행한다.


Replication ID explained
---

이전 섹션에서 우리는 두 인스턴스가 동일한 리플리케이션 ID와 리플리케이션 오프셋을 가지고 있다면, 그 둘은 완전히 동일한 데이터라고 이야기했다. 하지만 정확히 리플리케이션 ID가 무엇인지? 그리고 왜 인스턴스가 실제 메인 ID와 세컨더리 ID, 2개의 리플리케이션 ID를 가지고 있는지를 이해하는 것에 유용하다.

리플리케이션 ID는 기본적으로 지정된 데이터 셋의 *이력(history)* 을 표시한다. 인스턴스가 마스터로 재시작하거나, 리플리카가 마스터로 승력될 때마다, 이 인스턴스에 대해서는 새로운 리플리케이션 ID가 생성된다. 마스터로 연결된 리플리카들은 핸드쉐이크 이후에 마스터의 리플리케이션 ID를 상속할 것이다. 그래서 동일한 ID를 가진 두 인스턴스는 잠재적으로 다른 시간에 동일한 데이터를 가지고 있다는 사실에 의해 연관된다.  논리적인 시간으로 작용하는 오프셋이다. 가장 많이 업데이트된 데이터 셋을 가지는 특정 이력(리플리케이션 ID)을 알기 위한 논리적인 시간으로 작동하는 오프셋이다.

예를 들어, 인스턴스 A와 B, 두 개의 인스턴스가 같은 리플리케이션 ID를 가지고 있지만, 하나는 오프셋이 1000, 그리고 다른 하나는 오프셋이 1023이라고 할 때, 첫 번째는 데이터 셋에 적용된 특정 커맨드가 없다는 것을 의미한다. 또한 A가 몇 개의 커맨드를 적용함으로써 B와 정확히 동일한 상태가 될 수 있다는 것을 의미한다.

왜 레디스 인스턴스가 2개의 리플리케이션을 가지고 있는지에 대한 이유는 마스터로 승격되는 리플리카 때문이다. 페일오버 이후, 승격된 리플리카는 여전히 지난 리플리케이션 ID가 무엇인지 기억해야할 필요가 있는데, 그러한 리플리케이션 ID가 이전의 마스터의 것 중에 하나이기 때문이다. 이러한 방식으로, 다른 리플리카가 새로운 마스터와 동기화할 때, 이전 마스터의 리플리케이션 ID를 이용해서 부분 재동기화를 시도한다. 이것은 예상한대로 동작하는데, 리플리카가 마스터로 승격될 때 세컨더리 ID를 메인 ID로 설정하고, ID 변경이 발생했을 때의 오프셋이 무엇인지를 기억하기 때문이다. 이 후, 새로운 히스토리가 시작되므로 새로운 랜덤 ID를 선택해서 사용한다. 새로운 리플리카들에 대한 연결을 처리할 때, 마스터는 리플리카들의 IDs와 오프셋을 현재의 ID와 세컨더리 ID (안전을 위해 지정된 오프셋까지)까지 일치시킨다. 즉, 이것은 페일오버 이후에 새롭게 승격된 마스터로 연결하려는 리플리카는 전체 동기화를 수행할 필요가 없다는 것을 의미한다.

이러한 경우에 왜 마스터로 승격된 리플리카가 페일오버 이후에 자신의 리플리케이션 ID를 변경해야하는지가 궁금할 것이다: 이전 마스터는 여전히 마스터로 동작하고 있을 수 있는데, 왜냐하면 일부 네트워크 파티션 때문이다. 동일한 리플리케이션 ID를 유지하는 것은 동일한 ID와 동일한 오프셋을 가진 임의의 2개의 인스턴스는 동일한 데이터 셋을 가지고 있다는 사실(fact)을 위반하기 때문이다.

Diskless replication
---

일반적으로 전체 재동기화(full resynchronization)는 디스크 상에 RDB를 파일로 만들어야하고, 그리고 나서 리플리카에게 데이터를 공급하기 위해서 그 RDB 파일을 디스크로부터 다시 로딩한다.

느린 디스크를 사용하는 마스터에게는 이것은 매우 스트레스를 주는 오퍼레이션이다. 레디스 2.8.18 버전은 디스크없는(diskless) 리플리케이션을 지원하는 첫 번째 버전이다. 이 설정은 자식 프로세스가 중간 저장소로써 디ㅅ크를 사용하지 않고 직접 RDB를 네트워크(wire)를 통해 리플리카로 보낸다.

Configuration
---

기본 레디스 리플리케이션을 구성하는 것은 별로 어렵지 않다(trival): 단지 다음의 열을 리플리카의 구성 파일에 추가하면 된다:

    replicaof 192.168.1.1 6379

물론 `192.168.1.1 6379`을 당신의 마스터의 IP(또는 호스트네임)과 포트로 바꿀 필요가 있다. 그렇지 않으면, `REPLICAOF` 커맨드를 호출할 수 있으며, 마스터 호스트는 리플리카와의 동기화를 시작할 것이다.

또한, 마스터가 부분 재동기화를 수행하기 위해서, 메모리를 사용하는 리플리케이션 백로그를 튜닝하기 위한 몇가지 파라미터 있다. 마스터가 메모리를 취하는. 해서. `redis.conf`의 예를 보세요. 자세한 정보는 레디스 배포판에 포함되어 있는 `redis.conf` 예제를 참고하라.

디스크없는 리플리케이션은 `repl-diskless-sync` 구성 파라미터를 이용해서 활성화될 수 있다. 첫 번째 리플리카의 연결 이후, 좀 더 많은 리플리카가 연결을 기다리기 위해서, 전송의 시작에 대한 지연은 `repl-diskless-sync-delay` 파라미터에 의해 제어된다. 자세한 내용은 레디스 배포판의 `redis.conf` 파일을 참고하라.

Read-only replica
---

레디스 2.6 이후, 리플리카는 읽기 전용 모드를 지원하는데 이것은 기본적으로 활성화되어 있다. 이 동작은 redis.conf의 `replica-read-only`(`slave-read-only`) 옵션에 의해 제어된다. 그리고 `CONFIG SET`을 이용해서 런타임으로 활성화 또는 비활성화하는 것이 가능하다.

읽기 전용(read-only) 리플리카는 모든 쓰기를 거부하므로, 실수로 리플리카에 쓰기를 하는 것은 가능하지 않다. 이것은 이 기능이 리플리카를 인터넷이나 좀 더 일반적으로 신뢰할 수 없는 클라이언트가 존재하는 네트워크에 노출하려는 의도가 있다는 의미는 아닌데, `DEBUG`와 같은 관리자 커맨드가 여전히 활성화되기 때문이다. 그러나, 읽기 전용 인스턴스의 보안은 redis.conf에서 `rename-command` 지시자를 이용해서 커맨드를 비활성화시킴으로써 향상될 수 있다.

당신은 아마 왜 읽기 전용의 설정을 되돌리고, 쓰기 오퍼레이션의 대상이 될 수 있는 인스턴스를 만들려고 하는지 궁금할 수 있다. 그러한 쓰기들은 리플리카와 마스터의 재동기화나 리플리카가 재시작된다면 버려지지만, 임시적인(또는 삭제 가능한) 데이터를 쓰기가 가능한 리플리카에 저장하기 위한 몇 가지 합리적인 사용 케이스가 있다. 

예를 들어, 느린 `Set`이나 `Sorted set` 오퍼레이션의 계산과 그러한 것들을 로컬 키로 저장하려는 것은 여러 번 (또는 자주) 목격되는 쓰기가 가능한 리플리카의 사용 예이다. 

하지만 **4.0 버전 이전의 쓰기가 가능한 리플리카는 TTL 설정을 가진 키의 만료시키는 것은 할 수가 없다**는 것을 주의해야한다. 이것은 임의의 키에 대해서 최대 TTL값을 설정하는 `EXPIRE` 또는 다른 커맨드를 사용하면, 키는 누락될 것이고, 읽기 커맨드로 그 키에 접근하려고 할 때에는 그 키를 더 이상 볼 수 없을 수도 있지만, 키의 집계에서 볼 수 있고, 여전히 메모리에도 남아있을 것이다. 그래서 일반적으로 쓰기가 가능한 리플리카(4.0 이전의 버전)와 TTL을 가지는 키를 혼합하면 문제가 발생할 것이다.

레디스 4.0 RC3과 그 이상의 버전에서는 완전히 이 문제를 해결했고, 이제는 쓰기가 가능한 리플리카는 마스터가 하는 것처럼 TTL을 가진 키들을 축출(evict)해낼 수 있는데, **63**보다 큰 DB 에서 쓰여진 키들은 제외된다. (그러나 기본적으로 레디스 인스턴스는 16개의 데이터베이스만을 가진다.)

또한 레디스 4.0 이후에는 리플리카 쓰기는 오직 로컬에서만이고, 그 인스턴스의 하위(sub) 리플리카로 연결된 인스턴스로는 전파되지는 않는다는 점을 주의해야한다. 대신 하위(sub) 리플리카는  항상 최상위 마스터가 중간 리플리카로 보내는 것과 동일한 리플리케이션 스트림을 수신한다. 다음의 구성을 예로 들면:

    A ---> B ---> C

`B`가 쓰기가 가능하더라도, `C`는 `B`의 쓰기를 보지 않고, 대신 마스터 인스턴스 `A`와 같은 동일한 데이터 셋을 가진다.

Setting a replica to authenticate to a master
---

만약, 마스터가 `requirepass`를 이용해서 패스워드를 지정했다면, 모든 동기화 오퍼레이션에 대해서 리플리카가 패스워드를 사용하도록 하는 것은 어렵지 않다.

실행중인 인스턴스에 수행하기 위해서는 `redis-cli`을 이용하고, 다음과 같이 입력한다:

    config set masterauth <password>

영구적으로 적용하기 위해서는, 설정 파일(redis.conf)에 이 옵션을 추가한다:

    masterauth <password>

Allow writes only with N attached replicas
---

Redis 2.8부터, 현재 적어도 N개의 리플리카가 마스터로 연결되었을 때에만 레디스 마스터가 쓰기 쿼리를 받아들이도록 하는 것이 가능하다. 

그러나, 레디스는 비동기 리플리케이션(asynchronous replication)을 사용하기 때문에, 리플리카가 실제로 지정된 쓰기를 전달받았는지를 보장하는 것은 가능하지 않다. 그래서 데이터 손실이 가능한 시간대는 항상 존재한다.

아래는 이 기능이 동작하는 방법에 대한 것이다:

* 레디스 리플리카는 매 초마다 마스터에 핑을 보내며 처리된 복제 스트림의 양에 대한 응답한다.
* 레디스 마스터는 모든 리플리카 각각으로부터 핑을 받은 가장 최근 시간을 기억한다.
* 유저는 초(second) 단위로 지정된 최대 시간보다 작은 지연 시간을 가지는 리플리카의 최소 수를 설정할 수 있다.

만약, M초보다 더 적은 지연(lag)를 가지는 리플리카가 적어도 N개 있다면, 쓰기는 받아들여질 것이다.

주어진 쓰기(write)에 대해서 일관성은 보장하지 않지만, 적어도 데이터 손실이 가능한 시간을 지정된 시간(초)로 제한시키는 것은 최선의 데이터 안정 메커니즘이라고 생각해볼 수 있다. 일반적으로 데이터 손실에 경계를 두는 것이 없는 것보다는 낫다.

만약 조건을 만족시키지 않는다면, 마스터는 대신 에러를 응답할 것이고, 쓰기(write)를 받아들이지 않을 것이다.

이 기능과 관련된 두 가지 파라미터가 있다:

* min-replicas-to-write `<number of replicas>`
* min-replicas-max-lag `<number of seconds>`

좀 더 상세한 정보는, 레디스 소스 배포판에 함께 포함된 예제 `redis.conf` 파일을 참고하라.

How Redis replication deals with expires on keys
---

레디스는 키가 제한된 생존 시간을 갖게 함으로써 만료시킨다. 그러한 기능은 인스턴스가 시간을 계산하는 능력에 달려 있지만, 레디스 리플리카는 심지어 루아(Lua) 스크립트를 사용해서 키를 변경할 때에도, 키를 만료시간과 함께 키를 정확하게 복제한다.

그러한 기능을 구현하기 위해서 레디스는 마스터와 리플리카의 시간(clock)을 동기화하는 능력에 의지하지 않는데, 이것은 해결될 수 없는 문제이고, 경쟁 상태와 데이터 셋의 불일치(divering)를 초래할 수 있다. 따라서, 레디스는 세가지의 주요 테크닉을 사용해서 만료된 키에 대해 리플리케이션이 동작하도록 한다:

1. 리플리카는 키를 만료시키지 않고, 대신 마스터가 키를 만료시키기를 기다린다. 마스터가 키를 만료시킬 때 (또는 LRU로 키가 제거되는), `DEL` 커맨드를 합성하고(synthesizes)하고, 이는 모든 리플리카로 전파된다.
2. 그러나 마스터에 의존적인(master-driven) 만료때문에 마스터가 제 때에 `DEL` 커맨드를 전달해줄 수 없을 때에는, 때때로 리플리카는 여전히 메모리에 이미 논리적으로 만료된 키를 가지고 있을 수도 있다. 이것을 다루기 위해서, 리플리카는 (마스터로부터 새로운 커맨드가 도착하더라도) 데이터 셋의 일관성을 위반하지 않는, **오직 읽기 연산(only for read operations)** 에 대해서만 키가 존재하지 않는다고 보고하기 위해서 자신의 논리적인 시간(logical clock)을 이용한다. 이러한 방식으로 리플리카는 논리적으로 만료된 키가 여전히 존재한다고 보고하지 않도록 한다. 실질적인 사례에서, 확장을 위해 리플리카를 사용하는 HTML 엘리먼트 조각(fragments)의 캐시는 이미 TTL시간보다 오래된 아이템을 반환하지 않도록 한다.
3. 루아(Lua) 스크립트의 실행동안 키 만료는 수행되지 않는다. 루아 스크립트를 실행할 때, 개념적으로 마스터상의 시간은 동결(frozen)되며, 그래서 주어진 키는 스크립트가 실행되는 시간 전체에 대해서 존재하거나 또는 존재하지 않게 된다. 이것은 스크립트의 실행 중간에 키를 만료되는 것을 방지하고, 데이터 셋에 대해 동일한 영향을 가지는 것을 보장하는 방식으로 동일한 스크립트를 리플리카로 보내기 위해서 필요로하다.

한 번 리플리카가 마스터로 승격되면, 독립적으로 키를 만료시키기 시작하고, 이전 마스터로부터의 어떤 도움도 요구하지 않는다.

Configuring replication in Docker and NAT
---

도커나 포트 포워딩을 이용하는 기타 다른 종류의 컨테이너, 또는 네트워크 주소 변환(Network Address Translation) 사용될 때, 레디스 리플리케이션은 좀 더 추가적인 처리가 필요한데, 특히 리플리카의 주소를 발견하기 위해서 마스터의 `INFO`나 `ROLE`커맨드 출력결과를 스캔하는 레디스 센티널이나 기타 다른 시스템이 사용될 때가 그러하다.

문제는 마스터 인스턴스에서 실행된 `ROLE`커맨드 또는 `INFO`커맨드의 replication 섹션의 출력 결과는 리플리카가 마스터로 연결하기 위해서 사용한 IP주소를 보여주는데, NAT를 사용하는 환경 등에서의 (클라이언트가 리플리카로 연결하기 위해 사용하는) 리플리카의 논리적인 주소와 비교해 다를 수 있다.

마찬가지로 리플리카는 `redis.conf`에 설정된 리스닝 포트와 함께 나열되는데, 포트가 다시 맵핑되는 경우에는 포워드되는 포트와는 다를 수 있다.

두 가지 이슈를 수정하기 위해서, Redis 3.2.2 부터는 리플리카가 임의의 IP와 포트 번호의 쌍을 마스터에게 전달하도록 강제하는 것이 가능하다.

사용해야하는 설정 지시자는 다음과 같다:

    replica-announce-ip 5.5.5.5
    replica-announce-port 1234

그리고 최신의 레디스 배포판의 `redis.conf` 예졔에 문서화되어 있다.

The INFO and ROLE command
---

마스터와 리플리카 인스턴스의 현재 리플리케이션 파라미터에 관한 많은 정보를 제공하는 2개의 레디스 커맨드가 있다. 첫째는 `INFO` 커맨드이다. `INFO replication`처럼 `replication` 인자와 함께 호출되면, 리플리케이션과 관련된 정보만 화면에 표시된다. 또, 다른 컴퓨터 친화적인 커맨드는 `ROLE`로써, 리플리케이션 오프셋과 연결된 리플리카의 목록 등과 함께, 마스터와 리플리카의 리플리케이션 상태에 대한 정보를 제공한다.

Partial resynchronizations after restarts and failovers
---

레디스 4.0이후, 페일오버 이후에 한 인스턴스가 마스터로 승격되었을 때, 이전 마스터의 리플리카와 여전히 부분 재동기화(partial resynchronization)를 수행할 수 있다. 그렇기 하기 위해, 리플리카는 이전 마스터의  리플리케이션 ID와 오프셋을 기억하므로, 심지어 오래된 리플리케이션 ID로 요청을 하더라도,백로그의 일부를 연결하려는 리플리카에게 제공할 수 있다. 

하지만 승격된 리플리카의 새로운 리플리케이션 ID는 별도의 데이터셋의 히스토리를 구성하기 때문에 달라질 것이다. 예를 들어, 마스터가 사용 가능한 상태로 돌아올 수 있고, 일정 시간동안 쓰기를 계속 받아들일 수 있는데, 그렇기 때문에 승격된 리플리카내에서 동일한 리플리케이션 ID를 사용하는 것은 "리플리케이션 ID와 오프셋의 쌍이 오직 하나의 데이터 셋만을 식별해야한다"는 룰을 위반한다.

게다가, 완만하게 전원이 꺼지고 재시작될 때, 리플리카는 그들의 마스터와 재동기화를 하기위해 필요한 정보를 `RDB`파일에 저장할 수 있다. 이것은 업그레이드 등의 경우에 유용하다. 이것이 팔요하다면, 리플리카에서 `save & quit` 작업을 수행하기 위해서 `SHUTDOWN` 커맨드를 사용하는 것이 좋다.

AOF 파일을 통해서 다시 시작된 리플리카를 부분 재동기화하는 것은 가능하지 않다. 하지만 인스턴스는 셧다운 전에 RDB 영속성으로 전환하고나서 재시작할 수 있고, 마지막으로 AOF를 다시 활성화할 수 있다.