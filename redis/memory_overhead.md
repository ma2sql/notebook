# Redis의 메모리 오버헤드에 대해서

어떤 프로젝트나 어플리케이션 개발에서 레디스를 사용하고자 할 때, 초기에 어떠한 규모로 레디스를 셋업해야하는지 고민이 될 것이다. 단순히 키와 값에 대한 길이, 그리고 적당한 조각화(fragmentation)를 고려해서 계산하면 되는 것일까? 하나 이상의 키, 값을 관리하기 위해서 레디스는 특별한 자료구조를 사용할 것이고, 그러한 자료 구조를 유지하기 위해서 키/값에 필요한 메모리 이외에 별도의 메모리가 필요하다. 또한,  레디스 4.0버전부터 지원되는 MEMORY 커맨드, 그리고 INFO 커맨드의 memory절에 표현되는 내용 중, overhead 관련한 항목이 존재한다. 

많은 수의 키를 저장하는 패턴을 가진 레디스 클러스터가 있었다. 키는 노드당 대략 1억건 정도였으며, 값은 bool 형태로 1 또는 0을 저장하기만 한다. 일반적으로 string 타입의 경우 키마다 오버헤드가 50바이트 정도가 있을 것을 예상, 키의 길이와 값을 포함해도 대략 100바이트 미만일 것으로 예상했다. 대략 10기가 언저리일 것이라고 예상했으나, 예상을 훨씬 뛰어넘어 20기가에 육박해버렸다. `MEMORY STATS`으로 확인해보니, 데이터셋만큼 오버헤드가 7-8기가 정도를 차지했고, ht와 expire 각각 5, 2기가 정도를 차지했다.

## MEMORY USAGE 가 메모리를 계산하는 방법
데이터 타입별, 인코딩별로 값(value)의 크기를 계산한다. 그리고 키의 길이를 계산한다. 마지막으로 키/값을 관리하는 dictEntry값을 계산한다. 이렇게 각각 계산된 3개의 값을 반환하게 된다. 아마도 5.0부터 `SAMPLES`이라는 옵션이 추가되었는데, 가량 데이터셋이 수많은 엘리먼트를 가지는 경우에는 각각의 엘리먼트의 크기에 대해서도 조사기 필요하게 되므로 계산 시간이 매우 지연될 수 있다. 이에, `SAMPLES`로 지정된 수만큼의 엘리먼트의 수로 평균 값을 적당히 계산하여, 전체 엘리먼트 수를 곱하는 형태로 연산의 수를 줄일 수가 있다. `SAMPLES`를 지정하지 않으면, 기본 5개의 엘리먼트만 계산하여, 0을 지정하는 경우 엘리먼트 전체를 대상으로 계산하게 된다.

- objectComputeSize
  - 키의 데이터 타입, 인코딩에 따라서 용량을 계산한다.
  - 가량 string의 경우에는
    - OBJ_ENCODING_INT: robj 크기를 그대로 반환
    - OBJ_ENCODING_RAW: robj->ptr의 영역의 크기와 robj 크기를 더한 값을 반환
    - OBJ_ENCODING_EMBSTR: robj->ptr이 가리키는 문자열의 크기와 robj 크기를 더한 값을 반환
- sdsAllocSize
  - 키의 길이에 대한 메모리 할당량을 반환
- sizeof(dictEn try)
  - 키/값을 저장하는 dictEntry의 크기를 반환


## 주요 구조체

### redisDb
```c
typedef struct redisDb {
    dict *dict;                 /* The keyspace for this DB */
    dict *expires;              /* Timeout of keys with a timeout set */
    dict *blocking_keys;        /* Keys with clients waiting for data (BLPOP)*/
    dict *ready_keys;           /* Blocked keys that received a PUSH */
    dict *watched_keys;         /* WATCHED keys for MULTI/EXEC CAS */
    int id;                     /* Database ID */
    long long avg_ttl;          /* Average TTL, just for stats */
    unsigned long expires_cursor; /* Cursor of the active expire cycle. */
    list *defrag_later;         /* List of key names to attempt to defrag one by one, gradually. */
} redisDb;
```
레디스의 database. 논리적인 데이터 공간. redis.conf의 databases 변수에 의해 공간의 개수를 정할 수 있는데, 기본값은 16이다.

### dict
```c
typedef struct dict {
    dictType *type;
    void *privdata;
    dictht ht[2];
    long rehashidx; /* rehashing not in progress if rehashidx == -1 */
    unsigned long iterators; /* number of iterators currently running */
} dict;
```
해시테이블을 보유하는 구조체. 기본적으로 키를 관리하기 위해 사용되나, ttl이 지정된 키, blocking key등등 다양한 종류의 키를 관리하는데 사용된다.

```c
/* This is our hash table structure. Every dictionary has two of this as we
 * implement incremental rehashing, for the old to the new table. */
typedef struct dictht {
    dictEntry **table;
    unsigned long size;
    unsigned long sizemask;
    unsigned long used;
} dictht;
```
**dictht**: 해시테이블로 버킷을 관리한다. 각각의 버킷은 dictEntry와 연결된다.

### dictEntry
```c
// 24 bytes
typedef struct dictEntry {
    void *key;
    union { 
        void *val;
        uint64_t u64;
        int64_t s64;
        double d;
    } v; // 공용체
    struct dictEntry *next;
} dictEntry;
```
키와 값의 포인터를 저장하며, 버킷에 연결된 dictEntry는 싱글 링크드 리스트로 연결된다.

### robj
```c
typedef struct redisObject {
    unsigned type:4;
    unsigned encoding:4;
    unsigned lru:LRU_BITS; /* LRU time (relative to global lru_clock) or
                            * LFU data (least significant 8 bits frequency
                            * and most significant 16 bits access time). */
    int refcount;
    void *ptr;
} robj;
// #define LRU_BITS 24
```
값(value)을 저장하기 위한 구조체. 참고로 클라이언트로부터 전달받아 아직 가공되기 이전의 문자열도 robj로 표현된다.

dictEntry가 가리키는 key와 val은 모두 robj (redisObject) 이다.

### sds
작성중


## 키스페이스(redisDb)내의 오버헤드 계산
![overhead](/images/redis_keyspace_overhead.jpg)

```c
/*  
 *  #define dictSlots(d) ((d)->ht[0].size+(d)->ht[1].size)
 *  #define dictSize(d) ((d)->ht[0].used+(d)->ht[1].used)
 */
mem = dictSize(db->dict) * sizeof(dictEntry) +
      dictSlots(db->dict) * sizeof(dictEntry*) +
      dictSize(db->dict) * sizeof(robj);
mh->db[mh->num_dbs].overhead_ht_main = mem;
mem_total+=mem;

mem = dictSize(db->expires) * sizeof(dictEntry) +
      dictSlots(db->expires) * sizeof(dictEntry*);
mh->db[mh->num_dbs].overhead_ht_expires = mem;
mem_total+=mem;
```
**overhead_ht_main**
- 다음의 각 항목을 계산 후, 합한 값이 오버헤드의 값이 된다.
    - [해시테이블의 used (실제 키의 수)] x [dictEntry의 사이즈.. 24바이트]
    - [해시테이블의 used (실제 키의 수)] x [robj의 사이즈.. 16바이트]
    - [해시테이블의 size (버킷<또는 슬롯>의 수)] x [dictEntry의 포인터.. 8바이트]

**overhead_ht_expires**
- 다음의 각 항목을 계산 후, 합한 값이 오버헤드의 값이 된다.
    - [해시테이블의 used (실제 키의 수)] x [dictEntry의 사이즈.. 24바이트]
    - [해시테이블의 size (버킷<또는 슬롯>의 수)] x [dictEntry의 포인터.. 16바이트]

**key**는 sds로 저장된다. 값은 **robj**로 저장된다.



- **dictht**: 해시테이블로 버킷을 관리한다. 각각의 버킷은 dictEntry와 연결된다.
- 
- **sds**: 키는 단일 문자열로 관리된다. 키 이외에도 문자열을 저장하고 표현하는데 사용된다.
- **robj**: 값(value)을 저장하기 위한 구조체. 참고로 클라이언트로부터 전달받아 아직 가공되기 이전의 문자열도 robj로 표현된다.