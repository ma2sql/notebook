# How Redis replication deals with expires on keys

Redis expires allow keys to have a limited time to live. Such a feature depends on the ability of an instance to count the time, however Redis slaves correctly replicate keys with expires, even when such keys are altered using Lua scripts.

To implement such a feature Redis cannot rely on the ability of the master and slave to have synchronized clocks, since this is a problem that cannot be solved and would result into race conditions and diverging data sets, so Redis uses three main techniques in order to make the replication of expired keys able to work:

Slaves don't expire keys, instead they wait for masters to expire the keys. When a master expires a key (or evict it because of LRU), it synthesizes a DEL command which is transmitted to all the slaves.

슬레이브는 키를 만료시키지 않는 대신, 마스터가 키를 만료시키기를 기다린다. 마스터가 키를 만료시킬 때 (또는, LRU에서 키를 제거할 때), DEL 커맨드로 변환되어 모든 슬레이브로 전송이 된다.

However because of master-driven expire, sometimes slaves may still have in memory keys that are already logically expired, since the master was not able to provide the DEL command in time. In order to deal with that the slave uses its logical clock in order to report that a key does not exist only for read operations that don't violate the consistency of the data set (as new commands from the master will arrive). In this way slaves avoid to report logically expired keys are still existing. In practical terms, an HTML fragments cache that uses slaves to scale will avoid returning items that are already older than the desired time to live.

마스터 의존적인 만료는, 때때로 슬레이브에는 아직 메모리 상에 논리적으로는 이미 만료된 키가 있을 수 있다. 마스터에서 그 시점에 DEL 커맨드롤 제공할 수 없을때. 슬레이브가 자신의 로지컬 클럭을 사용한다. 보고하기 위해서. 키가 존재하지 않는다. 오직 읽기 동작에 대해서만. 읽기 일관성을 위반하지 않는 (새로운 커맨드는 허용). 이러한 방법에서 슬레이브는 논리적인 만료키 아직 존재하는 것을 보고.

During Lua scripts executions no keys expires are performed. As a Lua script runs, conceptually the time in the master is frozen, so that a given key will either exist or not for all the time the script runs. This prevents keys to expire in the middle of a script, and is needed in order to send the same script to the slave in a way that is guaranteed to have the same effects in the data set.

Lua 스크립

Once a slave is promoted to a master it will start to expire keys independently, and will not require any help from its old master.
