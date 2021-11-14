# Redis Cluster Specification

Welcome to the **Redis Cluster Specification**. Here you'll find information about algorithms and design rationales of Redis Cluster. This document is a work in progress as it is continuously synchronized with the actual implementation of Redis.

## Main properties and rationales of the design

### Redis Cluster goals [DONE]

Redis Cluster is a distributed implementation of Redis with the following goals, in order of importance in the design:
레디스 클러스터는 설계에서 중요한 순서대로, 아래와 같은 목표를 가지는 레디스의 분산 형태의 구현이다.

* High performance and linear scalability up to 1000 nodes. There are no proxies, asynchronous replication is used, and no merge operations are performed on values.
* Acceptable degree of write safety: the system tries (in a best-effort way) to retain all the writes originating from clients connected with the majority of the master nodes. Usually there are small windows where acknowledged writes can be lost. Windows to lose acknowledged writes are larger when clients are in a minority partition.
* Availability: Redis Cluster is able to survive partitions where the majority of the master nodes are reachable and there is at least one reachable replica for every master node that is no longer reachable. Moreover using *replicas migration*, masters no longer replicated by any replica will receive one from a master which is covered by multiple replicas.

* 고성능, 그리고 선형으로 최대 1000개까지 확장이 가능하다. 프록시가 존재하지 않으며, 비동기 리플리케이션이 사용된다. 그리고 값(value)에 대한 병합 오퍼레이션이 수행되지 않는다.
* 허용 가능한 쓰기 안전도: 시스템은 과반수 이상의 마스터 노드와 연결된 클라이언트로부터 온 모든 쓰기를 (최선의 방식으로) 유지하려고 한다. 보통 승인된 (acknowledged) 쓰기가 손실될 수 있는 작은 시간대(window)가 존재한다. 클라이언트가 소수 파티션에 있을 때, 승인된 쓰기를 손실할 수 있는 시간대가 더 크다.
* 가용성: 레디스 클러스터는 과반수의 마스터 노드가 연결 가능한 상태이고, 더 이상 접속이 불가능한 각각의 마스터 노드에 대해서는 적어도 하나의 연결 가능한 리플리카가 있는 파티션에서는 살아남을 수 있다. 게다가 리플리카 마이그레이션(replica migration)을 이용해서, 어떤 리플라키에 의해서도 리플레케이션되고 있지 않은 마스터 노드는 다수의 리플리카를 보유하고 있는 마스터로부터 리플리카를 하나 받을 수 있다.

What is described in this document is implemented in Redis 3.0 or greater.
이 문서에서 설명된 것은 Redis 3.0 이상에서 구현된다.

### Implemented subset [DONE]

Redis Cluster implements all the single key commands available in the non-distributed version of Redis. Commands performing complex multi-key operations like Set type unions or intersections are implemented as well as long as the keys all hash to the same slot.
레디스 클러스터는 분산되지 않은 레디스의 버전에서 사용가능한 모든 단일 키 커맨드를 구현한다. 키가 모두 동일한 슬롯으로 해시된다면, 셋(Set) 타입의 합집합이나 교집합 연산과 같은 복잡한 멀티 키(multi-key) 오퍼레이션을 수행하는 커맨드도 구현된다.

Redis Cluster implements a concept called **hash tags** that can be used in order to force certain keys to be stored in the same hash slot. However during manual resharding, multi-key operations may become unavailable for some time while single key operations are always available.
레디스 클러스터는 특정 키들을 동일한 해시 슬롯에 저장되게 하기 위해서 사용될 수 있는 **hash tags**라고 불리는 개념을 구현한다. 그러나 메뉴얼 리샤딩 중에, 단일 키 오퍼레이션은 항상 사용이 가능한 것에 반해, 멀티 키(multi-key) 오퍼레이션은 특정 시간 동안은 사용할 수 없게 될 수도 있다.

Redis Cluster does not support multiple databases like the stand alone version of Redis. There is just database 0 and the `SELECT` command is not allowed.
레디스 클러스터는 레디스의 싱글 버전처럼 다중 데이터베이스를 지원하지는 않는다. 데이터베이스는 0번만 있으며, `SELECT` 커맨드는 허용되지 않는다.

### Clients and Servers roles in the Redis Cluster protocol [DONE]

In Redis Cluster nodes are responsible for holding the data, and taking the state of the cluster, including mapping keys to the right nodes. Cluster nodes are also able to auto-discover other nodes, detect non-working nodes, and promote replica nodes to master when needed in order to continue to operate when a failure occurs.
레디스 클러스터에서 노드는 데이터를 보관하고, 올바른 노드로 키를 맵핑하는 것을 포함하여 클러스터의 상태를 가져오는 역할을 한다. 또한 클러스터 노드는 자동으로 다른 노드를 발견할 수 있으며, 동작하지 않는 노드를 발견하고, 장애가 발생한 상황에서 계속 동작하기 위해 필요할 때, 리플리카 노드를 마스터로 승격시킬 수 있다. 

To perform their tasks all the cluster nodes are connected using a TCP bus and a binary protocol, called the **Redis Cluster Bus**. Every node is connected to every other node in the cluster using the cluster bus. Nodes use a gossip protocol to propagate information about the cluster in order to discover new nodes, to send ping packets to make sure all the other nodes are working properly, and to send cluster messages needed to signal specific conditions. The cluster bus is also used in order to propagate Pub/Sub messages across the cluster and to orchestrate manual failovers when requested by users (manual failovers are failovers which are not initiated by the Redis Cluster failure detector, but by the system administrator directly).

이러한 작업들을 실행하기 위해서 모든 클러스터 노드들은**레디스 클러스터 버스(Redis Cluster Bus)**라고 불리는 TCP 버스와 바이너리 프로토콜을 이용해서 연결되어 있다. 모든 노드는 클러스터 내의 다른 모든 노드와 클러스터 버스를 이용해서 연결되어 있다. 노드들은 새로운 노드를 찾기 위해서 클러스터에 관한 정보를 전파하거나, 다른 모든 노드가 적절히 동작하고 있는지를 확인하기 위해서 ping패킷을 보내거나, 그리고 특정한 컨디션을 알리기 위해서 필요한 클러스터 메시지를 보내기 위해서, 가십 프로토콜(gossip protocol)을 사용한다. 클러스터 버스는 또한 Pub/Sub 메시지를 클러스터 전체에 전파하기 위해서도 사용되고, 유저의 요청에 의한 메뉴얼 페일오버를 조정하기 위해서도 사용된다. (메뉴얼 페일오버는 레디스 클러스터의 장애 디텍터가 아닌, 시스템 관리자에 의해서 직접 시작하는 페일오버이다.)

Since cluster nodes are not able to proxy requests, clients may be redirected to other nodes using redirection errors `-MOVED` and `-ASK`. The client is in theory free to send requests to all the nodes in the cluster, getting redirected if needed, so the client is not required to hold the state of the cluster. However clients that are able to cache the map between keys and nodes can improve the performance in a sensible way.
클러스터 노드는 요청을 프록시(대신 전파)할 수 없기 때문에, 클라이언트는 `-MOVED`와  `-ASK` 리다이렉션 에러를 이용해서 다른 노드로 리다이렉트될 것이다. 클라이언트는 이론적으로 클러스터 내의 모든 노드로 자유롭게 요청을 보낼 수 있고, 필요하다면 리다이렉트되므로, 클라이언트는 클러스터의 상태를 유지할 필요가 없다. 하지만 키와 노드의 맵핑을 캐시할 수 있는 클라이언트는 합리적인 방식으로 성능을 향상시킬 수 있다.

### Write safety [DONE]

Redis Cluster uses asynchronous replication between nodes, and **last failover wins** implicit merge function. This means that the last elected master dataset eventually replaces all the other replicas. There is always a window of time when it is possible to lose writes during partitions. However these windows are very different in the case of a client that is connected to the majority of masters, and a client that is connected to the minority of masters.
레디스 클러스터는 노드 간에 비동기 리플리케이션과 **last failover wins**이라는 묵시적 병합 기능을 사용한다. 이것은 마지막으로 선출된 마스터 데이터 셋이 결국 모든 리플리카를 대체하게 되는 것을 의미한다. 파티션동안 쓰기 데이터를 손실할 수 있는 시간대는 항상 있다. 그러나 과반수의 마스터와 연결된 클라이언트와 소수의 마스터와 연결된 클라이언트 경우, 이러한 시간의 크기는 매우 다르다.

Redis Cluster tries harder to retain writes that are performed by clients connected to the majority of masters, compared to writes performed in the minority side. The following are examples of scenarios that lead to loss of acknowledged writes received in the majority partitions during failures:
레디스 클러스터는 소수의 마스터 측에서 실행된 쓰기와 비교해서 과반수의 마스터에 연결된 클라이언트로부터 실행된 쓰기를 유지하려고 더 열심히 노력한다. 다음은 클러스터가 실패하는 동안 과반수의 파티션에서의 수신한 승인된 쓰기의 손실이 이어질 수 있는 시나리오의 예이다.

1. A write may reach a master, but while the master may be able to reply to the client, the write may not be propagated to replicas via the asynchronous replication used between master and replica nodes. If the master dies without the write reaching the replicas, the write is lost forever if the master is unreachable for a long enough period that one of its replicas is promoted. This is usually hard to observe in the case of a total, sudden failure of a master node since masters try to reply to clients (with the acknowledge of the write) and replicas (propagating the write) at about the same time. However it is a real world failure mode.

2. Another theoretically possible failure mode where writes are lost is the following:

* A master is unreachable because of a partition.
* It gets failed over by one of its replicas.
* After some time it may be reachable again.
* A client with an out-of-date routing table may write to the old master before it is converted into a replica (of the new master) by the cluster.

1. 쓰기(writes)는 마스터에 도달할 수 있지만, 마스터가 클라이언트에 응답하는 동안, 쓰기는 마스터와 리플리카 노드 사이에서 사용되는 비동기 리플리케이션을 통해서 리플리카로 전파되지 못할 수도 있다. 만약 쓰기를 리플리카로 전달하지 못하고 마스터가 죽게 되고, 리플리카 중 하나가 승격될만큼 긴 시간동안 접근할 수 없다면, 쓰기는 영원히 잃게 될 것이다. 마스터는 클라이언트에게 쓰기의 승인에 대해서 응답하는 것과 리플리카에게 쓰기를 전파하는 것을 거의 동시에 하려고 하기 때문에, 갑작스럽게 마스터가 완전히 실패하는 경우에는 이러한 것은 관측하기가 어렵다. 하지만 이것은 현실 세계에서의 실패 케이스다.

2. 이론으로 쓰기가 손실될 수 있는 또 다른 실패 케이스는 다음과 같다.

* 마스터가 파티션으로 연결되지 않는 상태이다.
* 리플라키 중 하나로 페일오버 된다.
* 일정 시간 후에, 마스터는 다시 연결할 수 있는 상태가 된다.
* 갱신되지 않은 (out-of-date) 라우팅 테이블을 가진 클라이언트는 새로운 마스터의 리플리카로 변경되기 이전의 오래된 마스터로 쓰기를 시도할 수도 있다.

The second failure mode is unlikely to happen because master nodes unable to communicate with the majority of the other masters for enough time to be failed over will no longer accept writes, and when the partition is fixed writes are still refused for a small amount of time to allow other nodes to inform about configuration changes. This failure mode also requires that the client's routing table has not yet been updated.
두 번째 실패 케이스는 발생하기 어려운데, 충분히 페일오버가 될만큼의 시간동안 과반수의 다른 마스터와 통신할 수 없는 마스터는 더 이상 쓰기를 받아들이지 않을 것이고, 파티션이 해소될 때에도 다른 노드들이 구성 변경에 대해서 알릴 수 있도록 짧은 시간 동안에도 여전히 쓰기는 거절될 것이기 때문이다. 또한, 이 실패 케이스는 또한 클라이언트의 라우팅 테이블이 아직 업데이트 되어 있지 않았다는 조건도 필요하다.

Writes targeting the minority side of a partition have a larger window in which to get lost. For example, Redis Cluster loses a non-trivial number of writes on partitions where there is a minority of masters and at least one or more clients, since all the writes sent to the masters may potentially get lost if the masters are failed over in the majority side.
파티션의 소수 측을 대상으로하는 쓰기는 쓰기를 손실할 수 있는 시간대가 더 크다. 예를 들어, 레디스 클러스터는 소수의 마스터와 적어도 하나 이상의 클라이언트가 있는 파티션에서 적지 않은 수의 쓰기를 읽게 되는데, 마스터가 과반수 쪽에서 페일오버가 된다면 마스터로 전송된 모든 쓰기가 잠재적으로 손실될 수 있기 때문이다.

Specifically, for a master to be failed over it must be unreachable by the majority of masters for at least `NODE_TIMEOUT`, so if the partition is fixed before that time, no writes are lost. When the partition lasts for more than `NODE_TIMEOUT`, all the writes performed in the minority side up to that point may be lost. However the minority side of a Redis Cluster will start refusing writes as soon as `NODE_TIMEOUT` time has elapsed without contact with the majority, so there is a maximum window after which the minority becomes no longer available. Hence, no writes are accepted or lost after that time.

특히, 마스터가 페일오버되기 위해서는 적어도 `NODE_TIMEOUT`동안 과반수의 마스터에 의해서 접근할 수 없는 상태가 되어야 하고, 그래서 만약 파티션이 그 시간 이전에 해소되면, 쓰기의 손실은 없다. 파티션이 `NODE_TIMEOUT` 이상 지속될 때, `NODE_TIMEOUT` 시간까지 소수 측에서 실행된 모든 쓰기는 손실될 수도 있다. 그러나 소수 측의 레디스 클러스터는 `NODE_TIMEOUT`이 경과하자마자, 과반수 측과의 연락없이 쓰기를 거절하기 시작하므로, 최대의 시간이 존재하며, 그 이후에는 소수 쪽은 더 이상 사용할 수 없는 상태가 된다. 이런 이유로 이 시간 이후에는 쓰기는 받아들여지거나, 손실되지도 않는다.

### Availability [DONE]

Redis Cluster is not available in the minority side of the partition. In the majority side of the partition assuming that there are at least the majority of masters and a replica for every unreachable master, the cluster becomes available again after `NODE_TIMEOUT` time plus a few more seconds required for a replica to get elected and failover its master (failovers are usually executed in a matter of 1 or 2 seconds).
레디스 클러스터는 소수 측의 파티션에서는 사용할 수 없다. 적어도 과반수의 마스터와 연결 불가능한 모든 마스터 노드에 리플리카가 있는 과반수의 파티션을 가정할 때, 클러스터는 `NODE_TIMEOUT`과 추가로 리플리카가 마스터로 승격되고 자신의 마스터를 페일오버 하기 위해 필요한 2초 정도의 시간 후에, 다시 사용 가능해지는 상태가 된다. (페일오버는 보통 1에서 2초안에 실행된다.)

This means that Redis Cluster is designed to survive failures of a few nodes in the cluster, but it is not a suitable solution for applications that require availability in the event of large net splits.
이것은 레디스 클러스터가 클러스터 내의 몇 개의 노드의 실패에 살아남기 위해 디자인되었지만, 대규모 네트워크 스플릿과 같은 것에서 가용성이 필요한 어플리케이션에 대해서는 적합한 솔루션이 아니라는 것을 의미한다.

In the example of a cluster composed of N master nodes where every node has a single replica, the majority side of the cluster will remain available as long as a single node is partitioned away, and will remain available with a probability of `1-(1/(N*2-1))` when two nodes are partitioned away (after the first node fails we are left with `N*2-1` nodes in total, and the probability of the only master without a replica to fail is `1/(N*2-1))`.

각각 하나의 리플리카를 가지는 `N`개의 마스터 노드로 구성된 클러스터의 예에서, 클러스터의 과반수는 노드 하나가 파티션되어 있는 한은 가용성을 유지할 것이다. 그리고 2개의 노드가 파티션된다면, `1-(1/(N*2-1))`의 확률로 가용성을 유지할 것이다. (첫 번째 노드가 실패한 후에, 총 `N*2-1`개의 노드가 남아있고, 리플리카가 없는 마스터가 실패하게 될 확률은 `1/(N*2-1)`이다)

For example, in a cluster with 5 nodes and a single replica per node, there is a `1/(5*2-1) = 11.11%` probability that after two nodes are partitioned away from the majority, the cluster will no longer be available.
예를 들어, 각각 하나의 리플리카를 가지는 노드 5개의 클러스터에서, 2개의 마스터가 과반수에서 다시 파티션된 이후에 클러스터는 더 이상 사용할 수 없게 될 확률은 `1/(5*2-1) = 11.11%`이다.

Thanks to a Redis Cluster feature called **replicas migration** the Cluster availability is improved in many real world scenarios by the fact that replicas migrate to orphaned masters (masters no longer having replicas). So at every successful failure event, the cluster may reconfigure the replicas layout in order to better resist the next failure.
**리플리카 마이그레이션(replicas migration)**으로 불리는 레디스 클러스터의 기능은 리플리카를 고아(orphaned) 마스터(더 이상 리플리카를 가지고 있지 않은)로 마이그레이션한다는 점에서 현실 세계의 시나리오에서 클러스터 가용성을 향상시키는데 도움을 준다. 그래서 모든 성공적인 실패 이벤트에서, 클러스터는 다음 실패에 더 잘 대처하기 위해서 리플리카 배치를 재구성한다. 

### Performance [DONE]

In Redis Cluster nodes don't proxy commands to the right node in charge for a given key, but instead they redirect clients to the right nodes serving a given portion of the key space.
레디스 클러스터에서 노드는 커맨드를 주어진 키를 담당하는 올바른 노드로 전달하는 프록시로서의 역할을 하지 않는다. 대신 클라이언트에게 주어진 키 스페이스의 특정 부분을 서빙하는  올바른 노드로 다시 보내게 한다.

Eventually clients obtain an up-to-date representation of the cluster and which node serves which subset of keys, so during normal operations clients directly contact the right nodes in order to send a given command.
결국 클라이언트는 최신의 클러스터의 상태와 키의 서브셋을 어떤 노드가 담당하는지에 대한 정보를 얻고, 그래서 정상적인 작업중에 클라이언트는 주어진 커맨드를 전송하기 위해서 직접 올바른 노드로 접근한다.

Because of the use of asynchronous replication, nodes do not wait for other nodes' acknowledgment of writes (if not explicitly requested using the `WAIT` command).
비동기 리플리케이션이 사용하므로, (만약 `WAIT` 커맨드를 사용해서 명시적으로 요청하지 않았을 때) 노드는 다른 노드의 쓰기에 대한 승인(acknowledgment)를 기다리지 않는다. 

Also, because multi-key commands are only limited to *near* keys, data is never moved between nodes except when resharding.
또한, 멀티 키(multi-key) 커맨드는 *근처(near)*의 키에 대해서만 제한되기 때문에, 리샤딩을 제외하고 데이터는 절대 노드 사이에서 이동되지 않는다.

Normal operations are handled exactly as in the case of a single Redis instance. This means that in a Redis Cluster with N master nodes you can expect the same performance as a single Redis instance multiplied by N as the design scales linearly. At the same time the query is usually performed in a single round trip, since clients usually retain persistent connections with the nodes, so latency figures are also the same as the single standalone Redis node case.
일반적인 오퍼레이션들은 정확히 단일 레디스 인스턴스의 경우처럼 다루어진다. 이것은 `N`개의 마스터를 가지는 레디스 클러스터에서는 구조가 선형적으로 확장됨에 따라 단일 레디스 인스턴스가 `N`배만큼 늘어난 것과 같은 퍼포먼스를 예상할 수 있다는 것을 의미한다. 동시에 쿼리는 보통 한 번의 왕복(round-trip)으로 처리되는데, 클라이언트가 보통 노드와 영구적인 커넥션을 유지하기 때문으로, 따라서 레이턴시 수치 또한 단일 레디스 노드의 경우와 같다.

Very high performance and scalability while preserving weak but reasonable forms of data safety and availability is the main goal of Redis Cluster.
약하지만 합리적인 형태의 데이터 안정성과 가용성을 유지하면서, 매우 높은 성능과 확장성을 제공하는 것이 레디스 클러스터의 주요 목표이다.

### Why merge operations are avoided [DONE]

Redis Cluster design avoids conflicting versions of the same key-value pair in multiple nodes as in the case of the Redis data model this is not always desirable. Values in Redis are often very large; it is common to see lists or sorted sets with millions of elements. Also data types are semantically complex. Transferring and merging these kind of values can be a major bottleneck and/or may require the non-trivial involvement of application-side logic, additional memory to store meta-data, and so forth.

레디스 클러스터 디자인은 (항상 바람직한 것은 아닌) 레디스 데이터 모델의 경우처럼 동일한 키-값 쌍의 버전이 여러 노드에서 충돌되지 않도록 한다. 레디스의 값은 종종 매우 크다. 수백만개의 엘리먼트를 가진 리스트나 정렬된 셋에서 보이는 것이 일반적이다. 데이터 타입은 의미적으로도 매우 복잡하다. 이러한 종류의 값들을 전송하고 병합하는 것은 매우 큰 병목 현상이 될 수 있고, 또 어플리케이션 측의 로직의 적지않은 개입과, 메타 데이터를 저장하기 위한 추가적인 메모리 등이 필요할 수 있다.

There are no strict technological limits here. CRDTs or synchronously replicated state machines can model complex data types similar to Redis. However, the actual run time behavior of such systems would not be similar to Redis Cluster. Redis Cluster was designed in order to cover the exact use cases of the non-clustered Redis version.

여기에 엄격한 기술적 제한은 없다. CRDTs나 동기식으로 복제되는 상태 머신은 레디스와 유사한 복잡한 데이터 타입을 모델링할 수 있다. 그러나 그러한 시스템의 실제 런타임 동작은 레디스 클러스터와 비슷하지 않다. 레디스 클러스터는 논클러스터드 레디스 버전의 완전한 사용 케이스를 커버하기 위해서 설계되었다.

## Overview of Redis Cluster main components

### Keys distribution model [DONE]

The key space is split into 16384 slots, effectively setting an upper limit for the cluster size of 16384 master nodes (however the suggested max size of nodes is in the order of ~ 1000 nodes).

키 스페이스는 16384개의 슬롯으로 나누어지며, 실질적으로 16384개의 마스터 노드의 클러스터 사이즈는 실질적인 상한이 설정이다. (그러나 추천하는 최대 노드의 수는 1000개의 노드까지이다.)

Each master node in a cluster handles a subset of the 16384 hash slots. The cluster is **stable** when there is no cluster reconfiguration in progress (i.e. where hash slots are being moved from one node to another). When the cluster is stable, a single hash slot will be served by a single node (however the serving node can have one or more replicas that will replace it in the case of net splits or failures, and that can be used in order to scale read operations where reading stale data is acceptable).

클러스터 내의 각 마스터 노드는 16384개의 해시 슬롯에 대한 서브셋을 다룬다. 클러스터는 클러스터 재설정이 진행되고 있지 않을 때 안정적이다. (예를 들어, 해시 슬롯이 한 노드에서도 다른 한 노드로 이동되고 있거나 할 때). 클러스터가 안정적일 때, 단일 해시 슬롯은 하나의 노드에서만 다뤄질 것이다. (그러나 슬롯을 가지는 노드는 하나 이상의 리플리카를 가질 수도 있는데, 네트워크 파티션이나 실패 등의 이유로 마스터 노드를 대체할 수도 있고, 그렇기 때문에 오래된(stale) 데이터를 받아들일 수 있다면, 읽기 오퍼러에이션을 확장시킬 수 있다.)

The base algorithm used to map keys to hash slots is the following (read the next paragraph for the hash tag exception to this rule):
키를 해시 슬롯에 맵핑하기 위해서 사용되는 기본 알고리즘은 아래와 같다. (이 규칙에 대한 해시 태그의 예외에 대해서는 다음 단락을 참고...)

```
HASH_SLOT = CRC16(key) mod 16384
```

The CRC16 is specified as follows:

* Name: XMODEM (also known as ZMODEM or CRC-16/ACORN)
* Width: 16 bit
* Poly: 1021 (That is actually x^16 + x^12 + x^5 + 1)
* Initialization: 0000
* Reflect Input byte: False
* Reflect Output CRC: False
* Xor constant to output CRC: 0000
* Output for "123456789": 31C3

14 out of 16 CRC16 output bits are used (this is why there is a modulo 16384 operation in the formula above).
CRC16의 출력 비트 16개 중에서 14개가 사용된다. (이것은 위의 공식에서 모듈러 16384 연산이 있는 이유이다.)

In our tests CRC16 behaved remarkably well in distributing different kinds of keys evenly across the 16384 slots.
우리의 테스트에서 CRC16은 서로 다른 종류의 키를 16384개의 슬롯들로 고르게 분배하는 것에 아주 잘 작동했다.

**Note**: A reference implementation of the CRC16 algorithm used is available in the Appendix A of this document.
**Note**: CRC16 알고리즘에서 사용된 구현에 대한 레퍼런스 이 문서의 Appendix A에서 확인할 수 있다.

### Keys hash tags

There is an exception for the computation of the hash slot that is used in order to implement **hash tags**. Hash tags are a way to ensure that multiple keys are allocated in the same hash slot. This is used in order to implement multi-key operations in Redis Cluster.

해시 슬롯의 계산에는 예외가 있고, 이것은 **해시 태그(hash tags)**를 구현하기 위해서 사용된다. 해시 태그는 여러 키가 동일한 해시 슬롯에 할당되도록 하는 방법이다. 이것은 레디스 클러스터에서 멀티 키(multi-key) 오퍼레이션을 구현하기 위해서 사용된다.

In order to implement hash tags, the hash slot for a key is computed in a slightly different way in certain conditions. If the key contains a "{...}" pattern only the substring between `{` and `}` is hashed in order to obtain the hash slot. However since it is possible that there are multiple occurrences of `{` or `}` the algorithm is well specified by the following rules:

해시 태그를 구현하기 위해서, 특정 조건에서 키에 대한 해시 슬롯은 약간 다른 방식으로 계산된다. 만약, 키가 "{...}" 패턴을 포함하고 있다면, 해시 슬롯을 얻기 위해서 `{`와 `}`사이의 부분 문자열만 해시된다. 그러나 `{`나 `}`가 여러번 나타날 수 있기 때문에, 이 알고리즘은 다음과 같은 룰에 의해 지정된다.

* IF the key contains a `{` character.
* AND IF there is a `}` character to the right of `{`
* AND IF there are one or more characters between the first occurrence of `{` and the first occurrence of `}`.

* IF 키는 `{` 문자를 포함한다.
* AND IF `{`의 오른쪽에 `}` 문자가 있다.
* AND IF 처음 나타난 `{`와 처음 나타난 `}`사이에 하나 이상의 문자가 있다.

Then instead of hashing the key, only what is between the first occurrence of `{` and the following first occurrence of `}` is hashed.
그러면 키를 해싱하는 대신, 처음 나타난 `{`와 다음에 처음 나타난 `}`사이의 문자만 해시된다.

Examples:

* The two keys `{user1000}.following` and `{user1000}.followers` will hash to the same hash slot since only the substring `user1000` will be hashed in order to compute the hash slot.
* For the key `foo{}{bar}` the whole key will be hashed as usually since the first occurrence of `{` is followed by `}` on the right without characters in the middle.
* For the key `foo{{bar}}zap` the substring `{bar` will be hashed, because it is the substring between the first occurrence of `{` and the first occurrence of `}` on its right.
* For the key `foo{bar}{zap}` the substring `bar` will be hashed, since the algorithm stops at the first valid or invalid (without bytes inside) match of `{` and `}`.
* What follows from the algorithm is that if the key starts with `{}`, it is guaranteed to be hashed as a whole. This is useful when using binary data as key names.

* `{user1000}.following` 와 `{user1000}.followers` 2개의 키는 해시 슬롯을 계산하기 위해서 부분 문자열 `user1000`만 해시되기 때문에, 동일한 해시 슬롯으로 해시된다. 
* `foo{}{bar}`는 처음 나타난 `{`에 `}`가 잇따라 나오고 가운데에 문자가 없기 때문에, 보통의 경우와 같이 키 전체가 해시된다. 
* `foo{{bar}}zap`는 부분 문자열 `{bar`가 해시되는데, 그것이 처음 나타나는 `{`와 그 오른쪽에 처음 나타나는 `}`사이의 부분 문자열이기 때문이다.
* `foo{bar}{zap}`은 부분 문자열 `bar`가 해시되는데, 알고리즘은 첫번째로 유효하거나 유효하지 않은(내부에 바이트가 없는) `{`와 `}`의 일치에서 멈추기 때문이다.
* 알고리즘에 따라서, 만약 키가 `{}`로 시작하면, 이것은 키 전체가 해시되는 것이 보장된다. 이것은 바이너리 데이터를 키 이름으로 사용할 때 유용하다.

Adding the hash tags exception, the following is an implementation of the `HASH_SLOT` function in Ruby and C language.
해시 태그 예외를 추가한다면, 다음은 Ruby와 C로 작성된 `HASH_SLOT`의 구현이다.

Ruby example code:
```ruby
def HASH_SLOT(key)
    s = key.index "{"
    if s
        e = key.index "}",s+1
        if e && e != s+1
            key = key[s+1..e-1]
        end
    end
    crc16(key) % 16384
end
```

C example code:
```c
unsigned int HASH_SLOT(char *key, int keylen) {
    int s, e; /* start-end indexes of { and } */

    /* Search the first occurrence of '{'. */
    for (s = 0; s < keylen; s++)
        if (key[s] == '{') break;

    /* No '{' ? Hash the whole key. This is the base case. */
    if (s == keylen) return crc16(key,keylen) & 16383;

    /* '{' found? Check if we have the corresponding '}'. */
    for (e = s+1; e < keylen; e++)
        if (key[e] == '}') break;

    /* No '}' or nothing between {} ? Hash the whole key. */
    if (e == keylen || e == s+1) return crc16(key,keylen) & 16383;

    /* If we are here there is both a { and a } on its right. Hash
        * what is in the middle between { and }. */
    return crc16(key+s+1,e-s-1) & 16383;
}
```

### Cluster nodes attributes [DONE]

Every node has a unique name in the cluster. The node name is the hex representation of a 160 bit random number, obtained the first time a node is started (usually using /dev/urandom).
모든 노드는 클러스터 내에서 유니크한 이름을 가진다. 노드 이름은 160비트 랜덤 숫자의 헥사 표현식이고, 이것은 노드가 처음 시작될 때 획득하게 된다. (보통은 /dev/random을 사용한다.)
The node will save its ID in the node configuration file, and will use the same ID forever, or at least as long as the node configuration file is not deleted by the system administrator, or a *hard reset* is requested via the `CLUSTER RESET` command.
노드는 그 ID를 노드 구성 파일에 저장하고, 적어도 시스템 관리자에 의해서 노드 구성 파일이 삭제거나, 또는 `CLUSTER RESET` 커맨드로 *hard reset*이 실행되거나 하지 않는 한, 같은 ID를 영원히 사용하게 된다. 

The node ID is used to identify every node across the whole cluster. It is possible for a given node to change its IP address without any need to also change the node ID. The cluster is also able to detect the change in IP/port and reconfigure using the gossip protocol running over the cluster bus.
노드 ID는 전체 클러스터에서 모든 노드를 식별하기 위해서 사용된다. 주어진 노드ID에 대해서 IP 주소를 바꾸는 것은 노드 ID의 어떤 변경도 필요도 없이 가능하다. 클러스터는 IP/port 변화를 감지하고, 클러스터 버스를 통해 실행되는 가십 프로토콜을 이용해서 노드 정보를 재구성할 수 있다.

The node ID is not the only information associated with each node, but is the only one that is always globally consistent. Every node has also the following set of information associated. Some information is about the cluster configuration detail of this specific node, and is eventually consistent across the cluster. Some other information, like the last time a node was pinged, is instead local to each node.
노드 ID는 각 노드와 관련된 유일한 정보가 아니라, 전역적으로 항상 일관된 유일한 것이다. 모든 노드는 다음과 같이 연관된 정보의 집합을 가진다. 일부 정보는 특정 노드의 클러스터 구성의 상세한 정보에 관한 것이고, 결국 클러스터 전체에서 일관된다. 일부 다른 정보는 노드가 ping된 마지막 시간과 같은 것으로, 각 노드의 로컬을 대신한다.

Every node maintains the following information about other nodes that it is aware of in the cluster: The node ID, IP and port of the node, a set of flags, what is the master of the node if it is flagged as `replica`, last time the node was pinged and the last time the pong was received, the current *configuration epoch* of the node (explained later in this specification), the link state and finally the set of hash slots served.
모든 노드는 다음과 같이 클러스터 내에서 알고 있는 다른 노드에 관한 정보를 유지한다. 
* 노드의 ID
* IP 
* Port
* 플래그셋
* 마스터 노드 정보 (플래그가 `replica` 일때)
* 노드가 마지막으로 ping을 보낸 시간
* 노드가 마지막으로 pong을 받은 시간
* 노드의 현재 *configuration epoch* (이 문서의 뒷 부분에서 설명)
* 연결 상태
* 서빙하는 슬롯의 집합

A detailed [explanation of all the node fields](https://redis.io/commands/cluster-nodes) is described in the `CLUSTER NODES` documentation.
모든 노드 필드들에 대한 상세한 설명은 ([explanation of all the node fields](https://redis.io/commands/cluster-nodes)) `CLUSTER NODES` 문서에서 설명되어 있다.

The `CLUSTER NODES` command can be sent to any node in the cluster and provides the state of the cluster and the information for each node according to the local view the queried node has of the cluster.
`CLUSTER NODES` 커맨드는 클러스터 내에서 어느 노드에서나 실행될 수 있고, 쿼리된 노드가 가지고 있는 클러스터의 로컬 뷰에 따라서 클러스터의 상태와 각 노드의 정보를 제공한다.

The following is sample output of the `CLUSTER NODES` command sent to a master node in a small cluster of three nodes.
다음은 3개 노드의 작은 클러스터의 한 마스터에서 `CLUSTER NODES` 커맨드를 실행한 샘플 출력이다.
```
$ redis-cli cluster nodes
d1861060fe6a534d42d8a19aeb36600e18785e04 127.0.0.1:6379 myself - 0 1318428930 1 connected 0-1364
3886e65cc906bfd9b1f7e7bde468726a052d1dae 127.0.0.1:6380 master - 1318428930 1318428931 2 connected 1365-2729
d289c575dcbc4bdd2931585fd4339089e461a27d 127.0.0.1:6381 master - 1318428931 1318428931 3 connected 2730-4095
```

In the above listing the different fields are in order: node id, address:port, flags, last ping sent, last pong received, configuration epoch, link state, slots. Details about the above fields will be covered as soon as we talk of specific parts of Redis Cluster.
위에서 리스팅된 각각 다른 필드는 순서대로 정렬되어 있다: 노드 ID, 주소:포트, 플래그, 마지막으로 ping한 시간, 마지막으로 pong을 받은 시간, 컨피그레이션 에포크, 연결 상태, 슬롯.
위 필드의 상세한 내용은 레디스 클러스터의 특정 부분에 대해서 이야기할 때 바로 설명하게 될 것이다.

### The Cluster bus [DONE]

Every Redis Cluster node has an additional TCP port for receiving incoming connections from other Redis Cluster nodes. This port will be derived by adding 10000 to the data port or it can be specified with the cluster-port config. 
모든 레디스 클러스터 노드는 다른 클러스터 노드로부터 들어오는(incoming) 커넥션을 받기 위한 추가적인 TCP 포트를 가지고 있다. 이 포트는 데이터 포트에 10000을 더해서  자동으로 만들어지거나, 또는 cluster-port라는 설정으로 지정될 수도 있다.

Example 1:

If a Redis node is listening for client connections on port 6379, and you do not add cluster-port parameter in redis.conf, the Cluster bus port 16379 will be opened.
6379포트에서 클라이언트 커넥션을 수신 중이고, redis.conf에서 cluster-port 파라미터를 추가하지 않았다면, 클러스터 버스 포트는 16379가 사용된다.

Example 2:

If a Redis node is listening for client connections on port 6379, and you set cluster-port 20000 in redis.conf, the Cluster bus port 20000 will be opened.
6379포트에서 클라이언트 커넥션을 수신 중이고, redis.conf에서 cluster-port를 20000으로 지정했다면, 클러스터 버스 포트는 20000이 사용된다.

Node-to-node communication happens exclusively using the Cluster bus and the Cluster bus protocol: a binary protocol composed of frames of different types and sizes. The Cluster bus binary protocol is not publicly documented since it is not intended for external software devices to talk with Redis Cluster nodes using this protocol. However you can obtain more details about the Cluster bus protocol by reading the `cluster.h` and `cluster.c` files in the Redis Cluster source code.
노드간(node-to-node)의 통신은 클러스터 버스와 클러스터 버스 프로토콜 (다양한 타입과 크기의 프레임으로 구성되는 바이너리 프로토콜)을 이용해서 독립적으로 이루어진다. 클러스터 버스 바이너리 프로토콜은 공식적으로 문서화되지 않았는데, 이것이 외부 소프트웨어 장치가 이 프로토콜을 이용해서 레디스 클러스터와 통신하기 위한 것이 아니기 때문이다. 그러나 레디스 소스코드 내에서 `cluster.h`와 `cluster.c` 파일을 읽음으로써 프로토콜에 관한 상세한 정보를 획득할 수는 있다.

### Cluster topology [DONE]

Redis Cluster is a full mesh where every node is connected with every other node using a TCP connection.
레디스 클러스터는 모든 노드가 다른 모든 노드와 TCP 커넥션을 사용해서 연결되는 풀 메시(full mesh)의 구성이다.

In a cluster of N nodes, every node has N-1 outgoing TCP connections, and N-1 incoming connections.
N개의 클러스터 내에서, 모든 노드는 N-1의 outgoing커넥션과, N-1의 imcoming 커넥션을 가진다.

These TCP connections are kept alive all the time and are not created on demand. When a node expects a pong reply in response to a ping in the cluster bus, before waiting long enough to mark the node as unreachable, it will try to refresh the connection with the node by reconnecting from scratch.
이 TCP 커넥션들은 항상 keepalive으로 유지되며, 요청이 있을때마다 생성되는 것은 아니다. 노드가 클러스터 버스에서 ping에 대한 응답으로 pong 기다릴 때, 어떤 노드를 접속할 수 없는 상태로 표기할 만큼 충분히 오랜 시간이 지난 것이 아니라면, 처음부터 재연결함으로써 그 노드와의 커넥션을 새로 고치려고 할 것이다.

While Redis Cluster nodes form a full mesh, **nodes use a gossip protocol and a configuration update mechanism in order to avoid exchanging too many messages between nodes during normal conditions**, so the number of messages exchanged is not exponential.
레디스 클러스터 노드들은 풀 메시를 구성하지만, **노드들은 정상적인 조건에서 노드간의 너무 많은 메시지 교환을 피하기 위해서 가십 프로토콜과 구성 정보 업데이트 메커니즘을 사용한다**. 그래서 교환되는 메시지의 수는 기하급수적으로 많지는 않다.

### Nodes handshake [DONE]

Nodes always accept connections on the cluster bus port, and even reply to pings when received, even if the pinging node is not trusted. However, all other packets will be discarded by the receiving node if the sending node is not considered part of the cluster.

노드는 클러스터 버스 포트로부터의 커넥션을 항상 받아들이고, 심지어 ping을 보낸 노드가 신뢰할 수 없더라도, 수신이 된다면 ping을 응답한다. 그러나 만약 보내는 노드가 클러스터의 일부로 간주되지 않는다면, 수신하는 노드에서 다른 모든 패킷들은 삭제될 것이다. 

A node will accept another node as part of the cluster only in two ways:
노드는 아래의 두 가지 방식으로만 클러스터의 멤버로서 다른 노드를 받아들인다:

* If a node presents itself with a `MEET` message. A meet message is exactly like a `PING` message, but forces the receiver to accept the node as part of the cluster. Nodes will send `MEET` messages to other nodes **only if** the system administrator requests this via the following command:

* 만약 노드가 그 자신을 `MEET` 메시지로 나타낸다면, MEET 메시지는 `PING` 메시지와 정확히 같지만, 수신하는 노드에게 클러스터의 일부로 받아들이도록 한다. **오직** 관리자가 다음의 커맨드로 요청할 때에만, 노드는 `MEET` 메시지를 다른 노드로 보낸다.

```
CLUSTER MEET ip port
```

* A node will also register another node as part of the cluster if a node that is already trusted will gossip about this other node. So if A knows B, and B knows C, eventually B will send gossip messages to A about C. When this happens, A will register C as part of the network, and will try to connect with C.

* 만약, 이미 신뢰한 노드가 다른 노드에 대해서 가십 메시지를 보내면, 수신하는 노드는 다른 노드를 클러스터의 일부로 등록할 것이다. 그래서 만약 A가 B를 알고, B가 C를 안다면, 결국 B는 A에게 C에 관한 가십 메시지를 보낼 것이다. 이것이 일어나면, A는 C를 네트워크의 일부로 등록할 것이고, C와 연결하려고 시도할 것이다.

This means that as long as we join nodes in any connected graph, they'll eventually form a fully connected graph automatically. This means that the cluster is able to auto-discover other nodes, but only if there is a trusted relationship that was forced by the system administrator.

이것은 연결된 그래프에 노드를 연결하는 한, 결국 자동으로 완전히 연결된 그래프 형태가 된다는 것을 의미한다. 이것은 클러스터가 자동으로 다른 노드를 발견할 수 있지만, 시스템 관리자가 만든 신뢰할 수 있는 관계가 있는 경우에만 가능하다.

This mechanism makes the cluster more robust but prevents different Redis clusters from accidentally mixing after change of IP addresses or other network related events.
이 메커니즘은 클러스터를 더 견고(완고)하게 만들지만, 아이피 주소의 변경이나 네트워크 관련된 이벤트가 발생한 이후에 서로 다른 레디스 클러스터 실수로 섞여버리는 것을 막아준다.


## Redirection and resharding

### MOVED Redirection

A Redis client is free to send queries to every node in the cluster, including replica nodes. The node will analyze the query, and if it is acceptable (that is, only a single key is mentioned in the query, or the multiple keys mentioned are all to the same hash slot) it will lookup what node is responsible for the hash slot where the key or keys belong.

If the hash slot is served by the node, the query is simply processed, otherwise the node will check its internal hash slot to node map, and will reply to the client with a MOVED error, like in the following example:

```
GET x
-MOVED 3999 127.0.0.1:6381
```

The error includes the hash slot of the key (3999) and the ip:port of the instance that can serve the query. The client needs to reissue the query to the specified node's IP address and port. Note that even if the client waits a long time before reissuing the query, and in the meantime the cluster configuration changed, the destination node will reply again with a MOVED error if the hash slot 3999 is now served by another node. The same happens if the contacted node had no updated information.

So while from the point of view of the cluster nodes are identified by IDs we try to simplify our interface with the client just exposing a map between hash slots and Redis nodes identified by IP:port pairs.

The client is not required to, but should try to memorize that hash slot 3999 is served by 127.0.0.1:6381. This way once a new command needs to be issued it can compute the hash slot of the target key and have a greater chance of choosing the right node.

An alternative is to just refresh the whole client-side cluster layout using the `CLUSTER NODES` or `CLUSTER SLOTS` commands when a MOVED redirection is received. When a redirection is encountered, it is likely multiple slots were reconfigured rather than just one, so updating the client configuration as soon as possible is often the best strategy.

Note that when the Cluster is stable (no ongoing changes in the configuration), eventually all the clients will obtain a map of hash slots -> nodes, making the cluster efficient, with clients directly addressing the right nodes without redirections, proxies or other single point of failure entities.

A client **must be also able to handle -ASK redirections** that are described later in this document, otherwise it is not a complete Redis Cluster client.

### Cluster live reconfiguration

Redis Cluster supports the ability to add and remove nodes while the cluster is running. Adding or removing a node is abstracted into the same operation: moving a hash slot from one node to another. This means that the same basic mechanism can be used in order to rebalance the cluster, add or remove nodes, and so forth.

* To add a new node to the cluster an empty node is added to the cluster and some set of hash slots are moved from existing nodes to the new node.
* To remove a node from the cluster the hash slots assigned to that node are moved to other existing nodes.
* To rebalance the cluster a given set of hash slots are moved between nodes.

The core of the implementation is the ability to move hash slots around. From a practical point of view a hash slot is just a set of keys, so what Redis Cluster really does during *resharding* is to move keys from an instance to another instance. Moving a hash slot means moving all the keys that happen to hash into this hash slot.

To understand how this works we need to show the `CLUSTER` subcommands that are used to manipulate the slots translation table in a Redis Cluster node.

The following subcommands are available (among others not useful in this case):

* `CLUSTER ADDSLOTS` slot1 [slot2] ... [slotN]
* `CLUSTER DELSLOTS` slot1 [slot2] ... [slotN]
* `CLUSTER SETSLOT` slot NODE node
* `CLUSTER SETSLOT` slot MIGRATING node
* `CLUSTER SETSLOT` slot IMPORTING node

The first two commands, `ADDSLOTS` and `DELSLOTS`, are simply used to assign (or remove) slots to a Redis node. Assigning a slot means to tell a given master node that it will be in charge of storing and serving content for the specified hash slot.

After the hash slots are assigned they will propagate across the cluster using the gossip protocol, as specified later in the *configuration propagation* section.

The `ADDSLOTS` command is usually used when a new cluster is created from scratch to assign each master node a subset of all the 16384 hash slots available.

The `DELSLOTS` is mainly used for manual modification of a cluster configuration or for debugging tasks: in practice it is rarely used.

The `SETSLOT` subcommand is used to assign a slot to a specific node ID if the `SETSLOT <slot> NODE` form is used. Otherwise the slot can be set in the two special states `MIGRATING` and `IMPORTING`. Those two special states are used in order to migrate a hash slot from one node to another.

* When a slot is set as MIGRATING, the node will accept all queries that are about this hash slot, but only if the key in question exists, otherwise the query is forwarded using a `-ASK` redirection to the node that is target of the migration.
* When a slot is set as IMPORTING, the node will accept all queries that are about this hash slot, but only if the request is preceded by an `ASKING` command. If the `ASKING` command was not given by the client, the query is redirected to the real hash slot owner via a `-MOVED` redirection error, as would happen normally.

Let's make this clearer with an example of hash slot migration.
Assume that we have two Redis master nodes, called A and B.
We want to move hash slot 8 from A to B, so we issue commands like this:

* We send B: CLUSTER SETSLOT 8 IMPORTING A
* We send A: CLUSTER SETSLOT 8 MIGRATING B

All the other nodes will continue to point clients to node "A" every time they are queried with a key that belongs to hash slot 8, so what happens is that:

* All queries about existing keys are processed by "A".
* All queries about non-existing keys in A are processed by "B", because "A" will redirect clients to "B".

This way we no longer create new keys in "A". In the meantime, `redis-cli` used during reshardings and Redis Cluster configuration will migrate existing keys in hash slot 8 from A to B.
This is performed using the following command:

```
CLUSTER GETKEYSINSLOT slot count
```

The above command will return `count` keys in the specified hash slot. For keys returned, `redis-cli` sends node "A" a `MIGRATE` command, that will migrate the specified keys from A to B in an atomic way (both instances are locked for the time (usually very small time) needed to migrate keys so there are no race conditions). This is how `MIGRATE` works:

```
MIGRATE target_host target_port "" target_database id timeout KEYS key1 key2 ...
```

`MIGRATE` will connect to the target instance, send a serialized version of the key, and once an OK code is received, the old key from its own dataset will be deleted. From the point of view of an external client a key exists either in A or B at any given time.

In Redis Cluster there is no need to specify a database other than 0, but `MIGRATE` is a general command that can be used for other tasks not involving Redis Cluster. `MIGRATE` is optimized to be as fast as possible even when moving complex keys such as long lists, but in Redis Cluster reconfiguring the cluster where big keys are present is not considered a wise procedure if there are latency constraints in the application using the database.

When the migration process is finally finished, the `SETSLOT <slot> NODE <node-id>` command is sent to the two nodes involved in the migration in order to set the slots to their normal state again. The same command is usually sent to all other nodes to avoid waiting for the natural propagation of the new configuration across the cluster.

### ASK redirection

In the previous section we briefly talked about ASK redirection. Why can't we simply use MOVED redirection? Because while MOVED means that we think the hash slot is permanently served by a different node and the next queries should be tried against the specified node, ASK means to send only the next query to the specified node.

This is needed because the next query about hash slot 8 can be about a key that is still in A, so we always want the client to try A and then B if needed. Since this happens only for one hash slot out of 16384 available, the performance hit on the cluster is acceptable.

We need to force that client behavior, so to make sure that clients will only try node B after A was tried, node B will only accept queries of a slot that is set as IMPORTING if the client sends the ASKING command before sending the query.

Basically the ASKING command sets a one-time flag on the client that forces a node to serve a query about an IMPORTING slot.

The full semantics of ASK redirection from the point of view of the client is as follows:

* If ASK redirection is received, send only the query that was redirected to the specified node but continue sending subsequent queries to the old node.
* Start the redirected query with the ASKING command.
* Don't yet update local client tables to map hash slot 8 to B.

Once hash slot 8 migration is completed, A will send a MOVED message and the client may permanently map hash slot 8 to the new IP and port pair. Note that if a buggy client performs the map earlier this is not a problem since it will not send the ASKING command before issuing the query, so B will redirect the client to A using a MOVED redirection error.

Slots migration is explained in similar terms but with different wording (for the sake of redundancy in the documentation) in the `CLUSTER SETSLOT` command documentation.

### Clients first connection and handling of redirections

While it is possible to have a Redis Cluster client implementation that does not remember the slots configuration (the map between slot numbers and addresses of nodes serving it) in memory and only works by contacting random nodes waiting to be redirected, such a client would be very inefficient.

Redis Cluster clients should try to be smart enough to memorize the slots configuration. However this configuration is not *required* to be up to date. Since contacting the wrong node will simply result in a redirection, that should trigger an update of the client view.

Clients usually need to fetch a complete list of slots and mapped node addresses in two different situations:

* At startup in order to populate the initial slots configuration.
* When a `MOVED` redirection is received.

Note that a client may handle the `MOVED` redirection by updating just the moved slot in its table, however this is usually not efficient since often the configuration of multiple slots is modified at once (for example if a replica is promoted to master, all the slots served by the old master will be remapped). It is much simpler to react to a `MOVED` redirection by fetching the full map of slots to nodes from scratch.

In order to retrieve the slots configuration Redis Cluster offers an alternative to the `CLUSTER NODES` command that does not require parsing, and only provides the information strictly needed to clients.

The new command is called `CLUSTER SLOTS` and provides an array of slots ranges, and the associated master and replica nodes serving the specified range.

The following is an example of output of `CLUSTER SLOTS`:

```
127.0.0.1:7000> cluster slots
1) 1) (integer) 5461
   2) (integer) 10922
   3) 1) "127.0.0.1"
      2) (integer) 7001
   4) 1) "127.0.0.1"
      2) (integer) 7004
2) 1) (integer) 0
   2) (integer) 5460
   3) 1) "127.0.0.1"
      2) (integer) 7000
   4) 1) "127.0.0.1"
      2) (integer) 7003
3) 1) (integer) 10923
   2) (integer) 16383
   3) 1) "127.0.0.1"
      2) (integer) 7002
   4) 1) "127.0.0.1"
      2) (integer) 7005
```

The first two sub-elements of every element of the returned array are the start-end slots of the range. The additional elements represent address-port pairs. The first address-port pair is the master serving the slot, and the additional address-port pairs are all the replicas serving the same slot that are not in an error condition (i.e. the FAIL flag is not set).

For example the first element of the output says that slots from 5461 to 10922 (start and end included) are served by 127.0.0.1:7001, and it is possible to scale read-only load contacting the replica at 127.0.0.1:7004.

`CLUSTER SLOTS` is not guaranteed to return ranges that cover the full 16384 slots if the cluster is misconfigured, so clients should initialize the slots configuration map filling the target nodes with NULL objects, and report an error if the user tries to execute commands about keys that belong to unassigned slots.

Before returning an error to the caller when a slot is found to be unassigned, the client should try to fetch the slots configuration again to check if the cluster is now configured properly.

### Multiple keys operations

Using hash tags, clients are free to use multi-key operations. For example the following operation is valid:

```
MSET {user:1000}.name Angela {user:1000}.surname White
```

Multi-key operations may become unavailable when a resharding of the hash slot the keys belong to is in progress.

More specifically, even during a resharding the multi-key operations targeting keys that all exist and all still hash to the same slot (either the source or destination node) are still available.

Operations on keys that don't exist or are - during the resharding - split between the source and destination nodes, will generate a `-TRYAGAIN` error. The client can try the operation after some time, or report back the error.

As soon as migration of the specified hash slot has terminated, all multi-key operations are available again for that hash slot.

### Scaling reads using replica nodes

Normally replica nodes will redirect clients to the authoritative master for the hash slot involved in a given command, however clients can use replicas in order to scale reads using the `READONLY` command.

`READONLY` tells a Redis Cluster replica node that the client is ok reading possibly stale data and is not interested in running write queries.

When the connection is in readonly mode, the cluster will send a redirection to the client only if the operation involves keys not served by the replica's master node. This may happen because:

1. The client sent a command about hash slots never served by the master of this replica.
2. The cluster was reconfigured (for example resharded) and the replica is no longer able to serve commands for a given hash slot.

When this happens the client should update its hashslot map as explained in the previous sections.

The readonly state of the connection can be cleared using the `READWRITE` command.