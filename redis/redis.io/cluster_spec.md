# Redis Cluster Specification

Welcome to the **Redis Cluster Specification**. Here you'll find information about algorithms and design rationales of Redis Cluster. This document is a work in progress as it is continuously synchronized with the actual implementation of Redis.

## Main properties and rationales of the design

### Redis Cluster goals

레디스 클러스터는 설계에서 중요한 순서대로, 아래와 같은 목표를 가지는 레디스의 분산 형태의 구현이다.

* 고성능, 그리고 선형으로 최대 1000개까지 확장이 가능하다. 프록시가 존재하지 않으며, 비동기 리플리케이션이 사용된다. 그리고 값(value)에 대한 병합 오퍼레이션이 수행되지 않는다.
* 허용 가능한 쓰기 안전도: 시스템은 과반수 이상의 마스터 노드와 연결된 클라이언트로부터 온 모든 쓰기를 (최선의 방식으로) 유지하려고 한다. 보통 승인된 (acknowledged) 쓰기가 손실될 수 있는 작은 시간대(window)가 존재한다. 클라이언트가 소수 파티션에 있을 때, 승인된 쓰기를 손실할 수 있는 시간대가 더 크다.
* 가용성: 레디스 클러스터는 과반수의 마스터 노드가 연결 가능한 상태이고, 더 이상 접속이 불가능한 각각의 마스터 노드에 대해서는 적어도 하나의 연결 가능한 리플리카가 있는 파티션에서는 살아남을 수 있다. 게다가 리플리카 마이그레이션(replica migration)을 이용해서, 어떤 리플라키에 의해서도 리플레케이션되고 있지 않은 마스터 노드는 다수의 리플리카를 보유하고 있는 마스터로부터 리플리카를 하나 받을 수 있다.

이 문서에서 설명된 것은 Redis 3.0 이상에서 구현된다.

### Implemented subset

레디스 클러스터는 분산되지 않은 레디스의 버전에서 사용가능한 모든 단일 키 커맨드를 구현한다. 키가 모두 동일한 슬롯으로 해시된다면, 셋(Set) 타입의 합집합이나 교집합 연산과 같은 복잡한 멀티 키(multi-key) 오퍼레이션을 수행하는 커맨드도 구현된다.

레디스 클러스터는 특정 키들을 동일한 해시 슬롯에 저장되게 하기 위해서 사용될 수 있는 **hash tags**라고 불리는 개념을 구현한다. 그러나 메뉴얼 리샤딩 중에, 단일 키 오퍼레이션은 항상 사용이 가능한 것에 반해, 멀티 키(multi-key) 오퍼레이션은 특정 시간 동안은 사용할 수 없게 될 수도 있다.

레디스 클러스터는 레디스의 싱글 버전처럼 다중 데이터베이스를 지원하지는 않는다. 데이터베이스는 0번만 있으며, `SELECT` 커맨드는 허용되지 않는다.

### Clients and Servers roles in the Redis Cluster protocol

레디스 클러스터에서 노드는 데이터를 보관하고, 올바른 노드로 키를 맵핑하는 것을 포함하여 클러스터의 상태를 가져오는 역할을 한다. 또한 클러스터 노드는 자동으로 다른 노드를 발견할 수 있으며, 동작하지 않는 노드를 발견하고, 장애가 발생한 상황에서 계속 동작하기 위해 필요할 때, 리플리카 노드를 마스터로 승격시킬 수 있다. 

이러한 작업들을 실행하기 위해서 모든 클러스터 노드들은**레디스 클러스터 버스(Redis Cluster Bus)**라고 불리는 TCP 버스와 바이너리 프로토콜을 이용해서 연결되어 있다. 모든 노드는 클러스터 내의 다른 모든 노드와 클러스터 버스를 이용해서 연결되어 있다. 노드들은 새로운 노드를 찾기 위해서 클러스터에 관한 정보를 전파하거나, 다른 모든 노드가 적절히 동작하고 있는지를 확인하기 위해서 ping패킷을 보내거나, 그리고 특정한 컨디션을 알리기 위해서 필요한 클러스터 메시지를 보내기 위해서, 가십 프로토콜(gossip protocol)을 사용한다. 클러스터 버스는 또한 Pub/Sub 메시지를 클러스터 전체에 전파하기 위해서도 사용되고, 유저의 요청에 의한 메뉴얼 페일오버를 조정하기 위해서도 사용된다. (메뉴얼 페일오버는 레디스 클러스터의 장애 디텍터가 아닌, 시스템 관리자에 의해서 직접 시작하는 페일오버이다.)

클러스터 노드는 요청을 프록시(대신 전파)할 수 없기 때문에, 클라이언트는 `-MOVED`와  `-ASK` 리다이렉션 에러를 이용해서 다른 노드로 리다이렉트될 것이다. 클라이언트는 이론적으로 클러스터 내의 모든 노드로 자유롭게 요청을 보낼 수 있고, 필요하다면 리다이렉트되므로, 클라이언트는 클러스터의 상태를 유지할 필요가 없다. 하지만 키와 노드의 맵핑을 캐시할 수 있는 클라이언트는 합리적인 방식으로 성능을 향상시킬 수 있다.

### Write safety

레디스 클러스터는 노드 간에 비동기 리플리케이션과 **last failover wins**이라는 묵시적 병합 기능을 사용한다. 이것은 마지막으로 선출된 마스터 데이터 셋이 결국 모든 리플리카를 대체하게 되는 것을 의미한다. 파티션동안 쓰기 데이터를 손실할 수 있는 시간대는 항상 있다. 그러나 과반수의 마스터와 연결된 클라이언트와 소수의 마스터와 연결된 클라이언트 경우, 이러한 시간의 크기는 매우 다르다.

레디스 클러스터는 소수의 마스터 측에서 실행된 쓰기와 비교해서 과반수의 마스터에 연결된 클라이언트로부터 실행된 쓰기를 유지하려고 더 열심히 노력한다. 다음은 클러스터가 실패하는 동안 과반수의 파티션에서의 수신한 승인된 쓰기의 손실이 이어질 수 있는 시나리오의 예이다.

1. 쓰기(writes)는 마스터에 도달할 수 있지만, 마스터가 클라이언트에 응답하는 동안, 쓰기는 마스터와 리플리카 노드 사이에서 사용되는 비동기 리플리케이션을 통해서 리플리카로 전파되지 못할 수도 있다. 만약 쓰기를 리플리카로 전달하지 못하고 마스터가 죽게 되고, 리플리카 중 하나가 승격될만큼 긴 시간동안 접근할 수 없다면, 쓰기는 영원히 잃게 될 것이다. 마스터는 클라이언트에게 쓰기의 승인에 대해서 응답하는 것과 리플리카에게 쓰기를 전파하는 것을 거의 동시에 하려고 하기 때문에, 갑작스럽게 마스터가 완전히 실패하는 경우에는 이러한 것은 관측하기가 어렵다. 하지만 이것은 현실 세계에서의 실패 케이스다.

2. 이론으로 쓰기가 손실될 수 있는 또 다른 실패 케이스는 다음과 같다.

* 마스터가 파티션으로 연결되지 않는 상태이다.
* 리플라키 중 하나로 페일오버 된다.
* 일정 시간 후에, 마스터는 다시 연결할 수 있는 상태가 된다.
* 갱신되지 않은 (out-of-date) 라우팅 테이블을 가진 클라이언트는 새로운 마스터의 리플리카로 변경되기 이전의 오래된 마스터로 쓰기를 시도할 수도 있다.

두 번째 실패 케이스는 발생하기 어려운데, 충분히 페일오버가 될만큼의 시간동안 과반수의 다른 마스터와 통신할 수 없는 마스터는 더 이상 쓰기를 받아들이지 않을 것이고, 파티션이 해소될 때에도 다른 노드들이 구성 변경에 대해서 알릴 수 있도록 짧은 시간 동안에도 여전히 쓰기는 거절될 것이기 때문이다. 또한, 이 실패 케이스는 또한 클라이언트의 라우팅 테이블이 아직 업데이트 되어 있지 않았다는 조건도 필요하다.

파티션의 소수 측을 대상으로하는 쓰기는 쓰기를 손실할 수 있는 시간대가 더 크다. 예를 들어, 레디스 클러스터는 소수의 마스터와 적어도 하나 이상의 클라이언트가 있는 파티션에서 적지 않은 수의 쓰기를 읽게 되는데, 마스터가 과반수 쪽에서 페일오버가 된다면 마스터로 전송된 모든 쓰기가 잠재적으로 손실될 수 있기 때문이다.

특히, 마스터가 페일오버되기 위해서는 적어도 `NODE_TIMEOUT`동안 과반수의 마스터에 의해서 접근할 수 없는 상태가 되어야 하고, 그래서 만약 파티션이 그 시간 이전에 해소되면, 쓰기의 손실은 없다. 파티션이 `NODE_TIMEOUT` 이상 지속될 때, `NODE_TIMEOUT` 시간까지 소수 측에서 실행된 모든 쓰기는 손실될 수도 있다. 그러나 소수 측의 레디스 클러스터는 `NODE_TIMEOUT`이 경과하자마자, 과반수 측과의 연락없이 쓰기를 거절하기 시작하므로, 최대의 시간이 존재하며, 그 이후에는 소수 쪽은 더 이상 사용할 수 없는 상태가 된다. 이런 이유로 이 시간 이후에는 쓰기는 받아들여지거나, 손실되지도 않는다.

### Availability

레디스 클러스터는 소수 측의 파티션에서는 사용할 수 없다. 적어도 과반수의 마스터와 연결 불가능한 모든 마스터 노드에 리플리카가 있는 과반수의 파티션을 가정할 때, 클러스터는 `NODE_TIMEOUT`과 추가로 리플리카가 마스터로 승격되고 자신의 마스터를 페일오버 하기 위해 필요한 2초 정도의 시간 후에, 다시 사용 가능해지는 상태가 된다. (페일오버는 보통 1에서 2초안에 실행된다.)

이것은 레디스 클러스터가 클러스터 내의 몇 개의 노드의 실패에 살아남기 위해 디자인되었지만, 대규모 네트워크 스플릿과 같은 것에서 가용성이 필요한 어플리케이션에 대해서는 적합한 솔루션이 아니라는 것을 의미한다.

각각 하나의 리플리카를 가지는 `N`개의 마스터 노드로 구성된 클러스터의 예에서, 클러스터의 과반수는 노드 하나가 파티션되어 있는 한은 가용성을 유지할 것이다. 그리고 2개의 노드가 파티션된다면, `1-(1/(N*2-1))`의 확률로 가용성을 유지할 것이다. (첫 번째 노드가 실패한 후에, 총 `N*2-1`개의 노드가 남아있고, 리플리카가 없는 마스터가 실패하게 될 확률은 `1/(N*2-1)`이다)

예를 들어, 각각 하나의 리플리카를 가지는 노드 5개의 클러스터에서, 2개의 마스터가 과반수에서 다시 파티션된 이후에 클러스터는 더 이상 사용할 수 없게 될 확률은 `1/(5*2-1) = 11.11%`이다.

**리플리카 마이그레이션(replicas migration)**으로 불리는 레디스 클러스터의 기능은 리플리카를 고아(orphaned) 마스터(더 이상 리플리카를 가지고 있지 않은)로 마이그레이션한다는 점에서 현실 세계의 시나리오에서 클러스터 가용성을 향상시키는데 도움을 준다. 그래서 모든 성공적인 실패 이벤트에서, 클러스터는 다음 실패에 더 잘 대처하기 위해서 리플리카 배치를 재구성한다. 

### Performance

레디스 클러스터에서 노드는 커맨드를 주어진 키를 담당하는 올바른 노드로 전달하는 프록시로서의 역할을 하지 않는다. 대신 클라이언트에게 주어진 키 스페이스의 특정 부분을 서빙하는  올바른 노드로 다시 보내게 한다.

결국 클라이언트는 최신의 클러스터의 상태와 키의 서브셋을 어떤 노드가 담당하는지에 대한 정보를 얻고, 그래서 정상적인 작업중에 클라이언트는 주어진 커맨드를 전송하기 위해서 직접 올바른 노드로 접근한다.

비동기 리플리케이션이 사용하므로, (만약 `WAIT` 커맨드를 사용해서 명시적으로 요청하지 않았을 때) 노드는 다른 노드의 쓰기에 대한 승인(acknowledgment)를 기다리지 않는다. 

또한, 멀티 키(multi-key) 커맨드는 *근처(near)*의 키에 대해서만 제한되기 때문에, 리샤딩을 제외하고 데이터는 절대 노드 사이에서 이동되지 않는다.

일반적인 오퍼레이션들은 정확히 단일 레디스 인스턴스의 경우처럼 다루어진다. 이것은 `N`개의 마스터를 가지는 레디스 클러스터에서는 구조가 선형적으로 확장됨에 따라 단일 레디스 인스턴스가 `N`배만큼 늘어난 것과 같은 퍼포먼스를 예상할 수 있다는 것을 의미한다. 동시에 쿼리는 보통 한 번의 왕복(round-trip)으로 처리되는데, 클라이언트가 보통 노드와 영구적인 커넥션을 유지하기 때문으로, 따라서 레이턴시 수치 또한 단일 레디스 노드의 경우와 같다.

약하지만 합리적인 형태의 데이터 안정성과 가용성을 유지하면서, 매우 높은 성능과 확장성을 제공하는 것이 레디스 클러스터의 주요 목표이다.

### Why merge operations are avoided

레디스 클러스터 디자인은 (항상 바람직한 것은 아닌) 레디스 데이터 모델의 경우처럼 동일한 키-값 쌍의 버전이 여러 노드에서 충돌되지 않도록 한다. 레디스의 값은 종종 매우 크다. 수백만개의 엘리먼트를 가진 리스트나 정렬된 셋에서 보이는 것이 일반적이다. 데이터 타입은 의미적으로도 매우 복잡하다. 이러한 종류의 값들을 전송하고 병합하는 것은 매우 큰 병목 현상이 될 수 있고, 또 어플리케이션 측의 로직의 적지않은 개입과, 메타 데이터를 저장하기 위한 추가적인 메모리 등이 필요할 수 있다.

여기에 엄격한 기술적 제한은 없다. CRDTs나 동기식으로 복제되는 상태 머신은 레디스와 유사한 복잡한 데이터 타입을 모델링할 수 있다. 그러나 그러한 시스템의 실제 런타임 동작은 레디스 클러스터와 비슷하지 않다. 레디스 클러스터는 논클러스터드 레디스 버전의 완전한 사용 케이스를 커버하기 위해서 설계되었다.

## Overview of Redis Cluster main components

### Keys distribution model

키 스페이스는 16384개의 슬롯으로 나누어지며, 실질적으로 16384개의 마스터 노드의 클러스터 사이즈는 실질적인 상한이 설정이다. (그러나 추천하는 최대 노드의 수는 1000개의 노드까지이다.)

클러스터 내의 각 마스터 노드는 16384개의 해시 슬롯에 대한 서브셋을 다룬다. 클러스터는 클러스터 재설정이 진행되고 있지 않을 때 안정적이다. (예를 들어, 해시 슬롯이 한 노드에서도 다른 한 노드로 이동되고 있거나 할 때). 클러스터가 안정적일 때, 단일 해시 슬롯은 하나의 노드에서만 다뤄질 것이다. (그러나 슬롯을 가지는 노드는 하나 이상의 리플리카를 가질 수도 있는데, 네트워크 파티션이나 실패 등의 이유로 마스터 노드를 대체할 수도 있고, 그렇기 때문에 오래된(stale) 데이터를 받아들일 수 있다면, 읽기 오퍼러에이션을 확장시킬 수 있다.)

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

CRC16의 출력 비트 16개 중에서 14개가 사용된다. (이것은 위의 공식에서 모듈러 16384 연산이 있는 이유이다.)

우리의 테스트에서 CRC16은 서로 다른 종류의 키를 16384개의 슬롯들로 고르게 분배하는 것에 아주 잘 작동했다.

**Note**: CRC16 알고리즘에서 사용된 구현에 대한 레퍼런스 이 문서의 Appendix A에서 확인할 수 있다.

### Keys hash tags

해시 슬롯의 계산에는 예외가 있고, 이것은 **해시 태그(hash tags)**를 구현하기 위해서 사용된다. 해시 태그는 여러 키가 동일한 해시 슬롯에 할당되도록 하는 방법이다. 이것은 레디스 클러스터에서 멀티 키(multi-key) 오퍼레이션을 구현하기 위해서 사용된다.

해시 태그를 구현하기 위해서, 특정 조건에서 키에 대한 해시 슬롯은 약간 다른 방식으로 계산된다. 만약, 키가 "{...}" 패턴을 포함하고 있다면, 해시 슬롯을 얻기 위해서 `{`와 `}`사이의 부분 문자열만 해시된다. 그러나 `{`나 `}`가 여러번 나타날 수 있기 때문에, 이 알고리즘은 다음과 같은 룰에 의해 지정된다.

* IF 키는 `{` 문자를 포함한다.
* AND IF `{`의 오른쪽에 `}` 문자가 있다.
* AND IF 처음 나타난 `{`와 처음 나타난 `}`사이에 하나 이상의 문자가 있다.

그러면 키를 해싱하는 대신, 처음 나타난 `{`와 다음에 처음 나타난 `}`사이의 문자만 해시된다.

Examples:

* `{user1000}.following` 와 `{user1000}.followers` 2개의 키는 해시 슬롯을 계산하기 위해서 부분 문자열 `user1000`만 해시되기 때문에, 동일한 해시 슬롯으로 해시된다. 
* `foo{}{bar}`는 처음 나타난 `{`에 `}`가 잇따라 나오고 가운데에 문자가 없기 때문에, 보통의 경우와 같이 키 전체가 해시된다. 
* `foo{{bar}}zap`는 부분 문자열 `{bar`가 해시되는데, 그것이 처음 나타나는 `{`와 그 오른쪽에 처음 나타나는 `}`사이의 부분 문자열이기 때문이다.
* `foo{bar}{zap}`은 부분 문자열 `bar`가 해시되는데, 알고리즘은 첫번째로 유효하거나 유효하지 않은(내부에 바이트가 없는) `{`와 `}`의 일치에서 멈추기 때문이다.
* 알고리즘에 따라서, 만약 키가 `{}`로 시작하면, 이것은 키 전체가 해시되는 것이 보장된다. 이것은 바이너리 데이터를 키 이름으로 사용할 때 유용하다.

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

### Cluster nodes attributes

모든 노드는 클러스터 내에서 유니크한 이름을 가진다. 노드 이름은 160비트 랜덤 숫자의 헥사 표현식이고, 이것은 노드가 처음 시작될 때 획득하게 된다. (보통은 /dev/random을 사용한다.)
노드는 그 ID를 노드 구성 파일에 저장하고, 적어도 시스템 관리자에 의해서 노드 구성 파일이 삭제거나, 또는 `CLUSTER RESET` 커맨드로 *hard reset*이 실행되거나 하지 않는 한, 같은 ID를 영원히 사용하게 된다. 

노드 ID는 전체 클러스터에서 모든 노드를 식별하기 위해서 사용된다. 주어진 노드ID에 대해서 IP 주소를 바꾸는 것은 노드 ID의 어떤 변경도 필요도 없이 가능하다. 클러스터는 IP/port 변화를 감지하고, 클러스터 버스를 통해 실행되는 가십 프로토콜을 이용해서 노드 정보를 재구성할 수 있다.

노드 ID는 각 노드와 관련된 유일한 정보가 아니라, 전역적으로 항상 일관된 유일한 것이다. 모든 노드는 다음과 같이 연관된 정보의 집합을 가진다. 일부 정보는 특정 노드의 클러스터 구성의 상세한 정보에 관한 것이고, 결국 클러스터 전체에서 일관된다. 일부 다른 정보는 노드가 ping된 마지막 시간과 같은 것으로, 각 노드의 로컬을 대신한다.

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

모든 노드 필드들에 대한 상세한 설명은 ([explanation of all the node fields](https://redis.io/commands/cluster-nodes)) `CLUSTER NODES` 문서에서 설명되어 있다.

`CLUSTER NODES` 커맨드는 클러스터 내에서 어느 노드에서나 실행될 수 있고, 쿼리된 노드가 가지고 있는 클러스터의 로컬 뷰에 따라서 클러스터의 상태와 각 노드의 정보를 제공한다.

다음은 3개 노드의 작은 클러스터의 한 마스터에서 `CLUSTER NODES` 커맨드를 실행한 샘플 출력이다.
```
$ redis-cli cluster nodes
d1861060fe6a534d42d8a19aeb36600e18785e04 127.0.0.1:6379 myself - 0 1318428930 1 connected 0-1364
3886e65cc906bfd9b1f7e7bde468726a052d1dae 127.0.0.1:6380 master - 1318428930 1318428931 2 connected 1365-2729
d289c575dcbc4bdd2931585fd4339089e461a27d 127.0.0.1:6381 master - 1318428931 1318428931 3 connected 2730-4095
```

위에서 리스팅된 각각 다른 필드는 순서대로 정렬되어 있다: 노드 ID, 주소:포트, 플래그, 마지막으로 ping한 시간, 마지막으로 pong을 받은 시간, 컨피그레이션 에포크, 연결 상태, 슬롯.
위 필드의 상세한 내용은 레디스 클러스터의 특정 부분에 대해서 이야기할 때 바로 설명하게 될 것이다.

### The Cluster bus

모든 레디스 클러스터 노드는 다른 클러스터 노드로부터 들어오는(incoming) 커넥션을 받기 위한 추가적인 TCP 포트를 가지고 있다. 이 포트는 데이터 포트에 10000을 더해서  자동으로 만들어지거나, 또는 cluster-port라는 설정으로 지정될 수도 있다.

Example 1:

6379포트에서 클라이언트 커넥션을 수신 중이고, redis.conf에서 cluster-port 파라미터를 추가하지 않았다면, 클러스터 버스 포트는 16379가 사용된다.

Example 2:

6379포트에서 클라이언트 커넥션을 수신 중이고, redis.conf에서 cluster-port를 20000으로 지정했다면, 클러스터 버스 포트는 20000이 사용된다.

노드간(node-to-node)의 통신은 클러스터 버스와 클러스터 버스 프로토콜 (다양한 타입과 크기의 프레임으로 구성되는 바이너리 프로토콜)을 이용해서 독립적으로 이루어진다. 클러스터 버스 바이너리 프로토콜은 공식적으로 문서화되지 않았는데, 이것이 외부 소프트웨어 장치가 이 프로토콜을 이용해서 레디스 클러스터와 통신하기 위한 것이 아니기 때문이다. 그러나 레디스 소스코드 내에서 `cluster.h`와 `cluster.c` 파일을 읽음으로써 프로토콜에 관한 상세한 정보를 획득할 수는 있다.

### Cluster topology

레디스 클러스터는 모든 노드가 다른 모든 노드와 TCP 커넥션을 사용해서 연결되는 풀 메시(full mesh)의 구성이다.

N개의 클러스터 내에서, 모든 노드는 N-1의 outgoing커넥션과, N-1의 imcoming 커넥션을 가진다.

이 TCP 커넥션들은 항상 keepalive으로 유지되며, 요청이 있을때마다 생성되는 것은 아니다. 노드가 클러스터 버스에서 ping에 대한 응답으로 pong 기다릴 때, 어떤 노드를 접속할 수 없는 상태로 표기할 만큼 충분히 오랜 시간이 지난 것이 아니라면, 처음부터 재연결함으로써 그 노드와의 커넥션을 새로 고치려고 할 것이다.

레디스 클러스터 노드들은 풀 메시를 구성하지만, **노드들은 정상적인 조건에서 노드간의 너무 많은 메시지 교환을 피하기 위해서 가십 프로토콜과 구성 정보 업데이트 메커니즘을 사용한다**. 그래서 교환되는 메시지의 수는 기하급수적으로 많지는 않다.

### Nodes handshake

노드는 클러스터 버스 포트로부터의 커넥션을 항상 받아들이고, 심지어 ping을 보낸 노드가 신뢰할 수 없더라도, 수신이 된다면 ping을 응답한다. 그러나 만약 보내는 노드가 클러스터의 일부로 간주되지 않는다면, 수신하는 노드에서 다른 모든 패킷들은 삭제될 것이다. 

노드는 아래의 두 가지 방식으로만 클러스터의 멤버로서 다른 노드를 받아들인다:

* 만약 노드가 그 자신을 `MEET` 메시지로 나타낸다면, MEET 메시지는 `PING` 메시지와 정확히 같지만, 수신하는 노드에게 클러스터의 일부로 받아들이도록 한다. **오직** 관리자가 다음의 커맨드로 요청할 때에만, 노드는 `MEET` 메시지를 다른 노드로 보낸다.

```
CLUSTER MEET ip port
```

* 만약, 이미 신뢰한 노드가 다른 노드에 대해서 가십 메시지를 보내면, 수신하는 노드는 다른 노드를 클러스터의 일부로 등록할 것이다. 그래서 만약 A가 B를 알고, B가 C를 안다면, 결국 B는 A에게 C에 관한 가십 메시지를 보낼 것이다. 이것이 일어나면, A는 C를 네트워크의 일부로 등록할 것이고, C와 연결하려고 시도할 것이다.

이것은 연결된 그래프에 노드를 연결하는 한, 결국 자동으로 완전히 연결된 그래프 형태가 된다는 것을 의미한다. 이것은 클러스터가 자동으로 다른 노드를 발견할 수 있지만, 시스템 관리자가 만든 신뢰할 수 있는 관계가 있는 경우에만 가능하다.

이 메커니즘은 클러스터를 더 견고(완고)하게 만들지만, 아이피 주소의 변경이나 네트워크 관련된 이벤트가 발생한 이후에 서로 다른 레디스 클러스터 실수로 섞여버리는 것을 막아준다.


## Redirection and resharding

### MOVED Redirection

레디스 클라이언트는 클러스터 내에서 리플리카 노드를 포함한 모든 노드로 자유롭게 쿼리를 보낼 수 있다. 노드는 쿼리를 분석해서, 쿼리 내에서 오직 하나의 키만 언급되거나 또는 동일한 해시 슬롯의 다중 키라면, 키 또는 키들이 속한 해시 슬롯을 담당하는 노드가 무엇인지 찾을 것이다.

만약 해시 슬롯이 요청을 보낸 노드에 의해서 제공된다면, 쿼리는 간단히 처리될 것이고, 그렇지 않으면 노드는 내부의 해시 슬롯과 노드 맵을 체크하고, 다음의 예제처럼 클라이언트에게 MOVED에러를 응답할 것이다.

```
GET x
-MOVED 3999 127.0.0.1:6381
```

에러는 키의 해시 슬롯(3999)과 쿼리를 처리할 수 있는 인스턴스의 아이피:포트를 포함한다. 클라이언트는 지정된 아이피 주소와 포트로 쿼리를 다시 실행할 필요가 있다. 클라이언트가 쿼리를 다시 실행하기 전에 오랜 시간을 대기하고, 그 사이에 클러스터의 구성 정보가 변경되어, 해시 슬롯 3999가 또 다른 노드에 의해서 제공되고 있다면, 대상(destination)노드는 다시 MOVED 에러를 반환할 것이다. 접속해있는 노드가 업데이트된 정보를 가지고 있지 않은 경우에도 동일한 일이 발생할 수 있다.

그래서 클러스터 노드의 관점에서는 ID로 식별되지만, 레디스 개발자 측에서는 해시 슬롯과 아이피:포트의 쌍으로 식별되는 레디스 노드의 맵을 노출시키는 것으로 클라이언트와의 인터페이스를 단순화하려고 한다.

클라이언트는 필수는 아니지만, 해시 슬롯 3999는 127.0.0.1:6381에서 처리되고 있다는 것을 기억해야 한다. 이러한 방법으로 실행되어야 하는 새로운 커맨드가 있을 때, 대상 키의 해시 슬롯을 계산할 수 있고, 올바른 노드를 선택할 가능성이 높아진다.

대안으로는 MOVED 에러를 받았을 때, `CLUSTER NODES`나 `CLUSTER SLOTS` 커맨드를 이용해서 전체 클라이언트 측의 클러스터 레이아웃을 단순히 새로 고치는 것이다. 리다이렉션이 발생하면, 하나보다는 여러 슬롯이 재구성될 가능성이 있기 때문에, 가능한한 자주 클러스터 구성 정보를 업데이트하는 것이 가장 좋은 전략이다.

클러스터가 안정적일 때(구성 정보에 계획해서 변경되지 않는), 결국 모든 클라이언트는 해시 슬롯과 노드에 대한 맵을 얻게될 것이고, 클러스터를 효율적이게 만들고, 클라이언트는 리다이렉션이나 프록시, 또는 기타 단일 고장점(single point of failure)의 엔트리없이, 직접 올바른 노드의 주소를 찾을 것이다.

클라이언트는 또한 이 문서의 후반에 설명할 **-ASK 리다이렉션(-ASK redirections)**을 처리할 수 있어야 하고, 그렇지 않으면 완전한 레디스 클러스터 클라이언트가 아니다.

### Cluster live reconfiguration

레디스 클러스터는 클러스터가 동작하는 동안에 노드를 추가하고 삭제할 수 있는 기능을 제공한다. 노드를 추가하고 삭제하는 것은 해시 슬롯을 노드 한 노드에서 다른 노드로 이동시키는 것과 같은 오퍼레이션으로 추상화되어 있다. 이것은 클러스터를 리밸런싱하거나 또는 노드를 추가하거나 삭제하는 등등을 위해서 동일한 기본 메커니즘이 사용될 수 있다는 것을 의미한다.

* 새로운 노드를 클러스터로 추가하기 위해서 비어 있는 노드(empty node)는 클러스터에 추가되고, 일부 해시 슬롯의 집합이 기존 노드에서 새로운 노드로 이동된다.
* 클러스터에서 노드 하나를 삭제하기 위해서 그 노드로 할당되어 있는 해시 슬롯들은 기존의 다른 노드로 이동된다.
* 클러스터를 리밸런싱하기 위해서 주어진 해시 슬롯의 집합은 노드 사이에서 이동된다.

이 구현의 핵심은 해시 슬롯을 주변으로 이동시키는 기능이다. 실제적인 관점에서 해시 슬롯은 그저 키의 집합이며, 그래서 레디스 클러스터가 *리샤딩(resharding)* 리샤딩하는 동안에 실제로 하는 일은 키를 한 인스턴스에서 또다른 인스턴스로 이동시키는 것이다.

이것이 어떻게 동작하는지 이해하려면 레디스 클러스터 노드에서 슬롯 변환 테이블을 조작하기 위해서 사용되는 `CLUSTER`의 서브 커맨드를 보여줄 필요가 있다.

다음 서브 커맨드들은 사용할 수 있다.

* `CLUSTER ADDSLOTS` slot1 [slot2] ... [slotN]
* `CLUSTER DELSLOTS` slot1 [slot2] ... [slotN]
* `CLUSTER SETSLOT` slot NODE node
* `CLUSTER SETSLOT` slot MIGRATING node
* `CLUSTER SETSLOT` slot IMPORTING node

처음 두 커맨드 `ADDSLOTS`과 `DELSLOTS`는 단순히 한 레디스 노드로 슬롯을 할당하거나 제거하기 위해서 사용된다. 슬롯을 할당하는 것은 주어진 마스터 노드에게 지정된 해시 슬롯에 대한 내용들을 저장하고 제공하는 역할을 담당하게 될 것이라고 알리는 것을 의미한다.

해시 슬롯이 할당되면, 이후에 *구성 정보 전파(configuration propagation)* 섹션에서 명시된 것처럼, 가십 프로토콜을 이용해서 클러스터 전체에 전파 될 것이다. 

`ADDSLOTS` 커맨드는 보통 맨처음에 새로운 클러스터가 만들어졌을 때, 각 마스터 노드에 사용이 가능한 모든 16384개의 해시 슬롯의 서브셋을 할당하기 위해서 사용된다.

`DELSLOTS`는 주로 클러스터 구성의 수동 변경이나 디버깅 작업을 위해서 사용되고, 실제로 거의 사용되지 않는다.

`SETSLOT`서브 커맨드는 만약 `SETSLOT <slot> NODE`의 형태로 사용된다면, 슬롯을 지정된 노드ID로 슬롯을 할당하기 위해서 사용된다. 반면에 슬롯은 `MIGRATING`과 `IMPORTING`이라는 2개의 특별한 상태로 설정될 수 있다. 이러한 두 가지의 특별한 상태는 해시 슬롯을 한 노드에서 또 다른 노드로 마이그레이션하기 위해서 사용된다.

* 슬롯이 `MIGRATING`으로 설정되면, 오직 해당 키가 존재하는 경우에만, 노드는 그 해시 슬롯에 대한 모든 쿼리를 받아들인다. 그렇지 않으면 쿼리는 `-ASK` 리다이렉션을 이용해서 마이그레이션 대상 노드로 전달된다.
* 슬롯이 `IMPORTING`으로 설정되면, 오직 요청 앞에 `ASKING` 커맨드가 선행된 경우에만, 노드는 그 해시 슬롯에 대한 모든 쿼리를 받아들인다. 만약 클라이언트에 의해서 `ASKING` 커맨드가 주어지지 않는다면, 쿼리는 보통 발생하는 것처럼 `-MOVED` 에러를 통해서 실제 해시 슬롯의 주인으로 리다이렉트된다.

해시 슬롯의 마이그레이션의 예로 좀 더 명확히해보자.
A와 B의 2개의 레디스 마스터 노드를 가지고 있다고 가정하자.
해시 슬롯 8을 A에서 B로 옮기려고 하면, 다음과 같은 커맨드를 실행할 것이다.

* We send B: CLUSTER SETSLOT 8 IMPORTING A
* We send A: CLUSTER SETSLOT 8 MIGRATING B

다른 노드 모두는 해시 슬롯 8에 속한 키로 쿼리를 받을 때마다, 계속해서 클라이언트가 노드 "A"를 가리키도록 할 것이다.

* 존재하는 키에 대한 모든 쿼리는 "A"에 의해서 처리된다.
* A에 존재하지 않는 키에 대한 모든 쿼리는 "B"에 의해서 처리되기 때문에, "A"는 클라이언트를 "B"로 리다이렉트할 것이다.

이렇게 하면 더 이상 "A"에서 새로운 키를 만들지 않는다. 그동안 리샤딩과 레디스 클러스터 구성시에 사용되는 `redis-cli`는 해시 슬롯 8에 존재하는 키를 A에서 B로 마이그레이션할 것이다.
이것은 다음과 같은 커맨드로 수행된다.

```
CLUSTER GETKEYSINSLOT slot count
```

위의 커맨드는 지정된 해시 슬롯에서 `count`에 지정된 만큼의 키를 반환할 것이다. 반환되는 키에 대해서, `redis-cli`는 노드 "A"에 `MIGRATE` 커맨드를 전송하고, 지정된 키들은 노드 A에서 B로 원자적(atomic)인 방식으로 마이그레이션될 것이다. (두 인스턴스는 키를 옮기는데 필요로한 시간동안 아주 짧게 락이 걸리며, 그렇게 때문에 경쟁 상태*race condition*는 없다). 다음은 `MIGRATE`가 작동하는 방법에 대한 것이다.

```
MIGRATE target_host target_port "" target_database id timeout KEYS key1 key2 ...
```

`MIGREATE`는 대상 인스턴에서 접속하고, 키의 직렬화된 버전을 전송하고, OK 코드를 받으면, 자신의 데이터 셋에서 오래된 키들은 삭제가 될 것이다. 외부 클라이언트의 관점에서 키는 A또는 B 둘중 하나에서 언제나 존재하게 된다.

레디스 클러스터에서 0이외의 데이터베이스를 지정할 필요가 없지만, `MIGRATE`는 레디스 클러스터와 관련이 없는 다른 작업에서도 사용될 수 있는 일반적인 커맨드이다. `MIGRATE`는 리스트와 같이 복잡한 키를 옮길 때에도 가능한한 빠르게 최적화되지만, 레디스 클러스터에서 빅 키(big key)가 존재하는 클러스터를 재구성하는 것은 데이터베이스를 사용하는 어플리케이션에서 레이턴시 제약이 있는 경우에 현명한 절차로 간주되지 않는다. 

마이그레이션 절차가 최종적으로 완료되면, 슬롯들을 정상적인 상태로 다시 설정하기 위해서, `SETSLOT <slot> NODE <node-id>` 커맨드는 마이그레이션 절차에 포함된 2개의 노드에서 실행된다. 전체 클러스터로 새로운 구성이 자연스럽게 전파될 때까지 가디라지 않도록 일반적으로 동일한 코맨드는 모든 다른 노드로도 전송이 된다. 

### ASK redirection

이전 섹션에서 ASK 리다이렉션에 대해서 간략히 이야기했다. 단순하게 MOVED 리다이렉션을 사용할 수 없는 이유는 무엇일까? 왜냐하면 MOVED는 어떤 한 해시 슬롯은 영구적으로 다른 노드에 의해서 제공되고, 후속 쿼리들은 지정된 노드에서 시도되어야 한다는 것을 의미하지만, ASK는 오직 다음 쿼리 하나만 지정된 노드로 보내지는 것을 의미하기 때문이다.

이것은 해시 슬롯 8에 대한 다음 쿼리가 여전히 A에 남아있는 키에 대한 것이 될 수가 있기 때문에 필요하며, 그래서 항상 클라이언트는 A를 먼저 시도하고, 그리고 나서 필요하다면 B를 시도할 필요가 있다. 이것은 사용이 가능한 16384개의 슬롯 중에서 오직 하나의 해시 슬롯에 대해서만 발생하는 것이기 때문에, 클러스터에 대한 성능적인 영향은 수용이 가능하다.

클라이언트의 동작을 강제할 필요가 있고, 그래서 클라이언트가 노드 A에서 시도된 이후에만 노드 B에서 시도하도록 하게 하려면, 클라이언트가 쿼리를 보내기 전에 `ASKING` 커맨드를 보낸면, 노드 B는 IMPORTING 상태로 설정된 슬롯에 대한 쿼리만 받아들인다.

기본적으로 `ASKING` 커맨드는 노드가 클라이언트에게 IMPORTING 슬롯에 대한 쿼리를 처리하도록 하는 일회성 플래그를 설정한다.

클라이언트의 관점에서 ASK 리다이렉션의 전체적인 의미는 다음과 같다.

* 만약 ASK 리다이렉션을 받으면, 리다이렉트된 쿼리만 지정된 노드로 보내고, 후속 쿼리들은 계속해서 이전 노드로 보낸다.
* `ASKING` 커맨드로 리다이렉트된 쿼리를 시작한다.
* 아직 로컬 클라이언트 테이블에서 해시 슬롯 8을 노드 B로 업데이트 하지는 않아야 한다.

해시 슬롯 8의 마이그레이션이 완료되면, 노드 A는 MOVED 메시지를 보내고, 클라이언트는 영구적으로 해시 슬롯 8을 새로운 아이피와 포트의 쌍으로 매핑할 수 있을 것이다. 만약 버그가 있는 클라이언트에서 이러한 맵핑을 더 일찍 실행하는 경우에, 쿼리를 실행하기 이전에 ASKING 커맨드를 보내지 않을 것이기 때문에 이것은 문제가 되지 않고, 그래서 노드 B는 MOVED에러를 이용해서 클라이언트를 노드 A로 리다이렉트할 것이다.

슬롯 마이그레이션은 문서내의 불필요한 중복의 이유로, `CLUSTER SETSLOT` 커맨드의 문서에서 유사하지만 다른 용어로 설명한다.

### Clients first connection and handling of redirections

슬롯 번호와 그것을 제공하는 노드의 주소를 맵핑하는 슬롯 구성을 메모리상에 보존하지 않고, 리다이렉트 되기를 기다리며 랜덤한 노드에 접근하는 식으로만 동작하는 레디스 클라이언트 구현이 있을 수 있지만, 그러한 클라이언트는 매우 비효율적이다.

레디스 클러스터 클라이언트는 슬롯 구성을 기억할만큼 스마트해야 한다. 그러나 이 구성 정보는 최신 상태일 필요는 없다. 잘못된 노드로 연결하면 단순히 리다이렉션이되기 때문에, 클라이언트의 뷰의 업데이트를 발생시키면 된다.

클라이언트는 일반적으로 다음 2가지의 경우에 슬롯과 맵핑된 주소들을 전체 목록을 가져와야 한다.

* 시작시, 초기 슬롯 구성 정보를 채우기 위해서
* `MOVED` 리다이렉션을 수신했을 때

클라이언트는 이동된 슬롯에 대해서만 테이블을 업데이트함으로써 `MOVED` 리다이렉션을 처리할 수도 있지만, 여러 슬롯의 구성 정보가 한 번에 변경되는 일이 자주 있기 때문이, 일반적으로 이것은 효율적이지 못하다 (예를 들어, 리플리카가 마스터로 승격되면, 이전 마스터가 담당하던 모든 슬롯은 다시 맵핑되어야 한다). 처음부터 다시 슬롯과 노드의 전체 맵핑을 가져옴으로써 `MOVED` 리다이렉션에 대응하는 편이 훨씬 더 간단하다.

슬롯 구성 정보를 검색하기 위해서 레디스 클러스터는 파싱이 필요없는, `CLUSTER NODES`의 대안을 제안하며, 클라이언트에게 엄격히 필요한 정보만을 제공한다.

이 새로운 커맨드는 `CLUSTER SLOTS`라고 하며, 슬롯 범위의 배열과 지정된 범위를 처리하는 관련 마스터와 리플리카 노드를 제공한다.

다음은 `CLUSTER SLOTS`의 출력 결과의 예문이다.

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

반환되는 배열의 각 엘리먼트의 첫 두 서브 엘리먼트는 범위의 시작과 끝 슬롯이다. 추가적인 요소는 주소-포트의 쌍을 나타낸다. 첫 주소-포트의 쌍은 슬롯을 제공하는 마스터 노드이고, 그 이후의 주소-포트의 쌍들은 에러가 발생한 상태가 아닌(예를 들어, FAIL 플래그가 설정되지 않은 등등), 동일한 슬롯을 제공하는 모든 리플리카에 대한 것이다.

예를 들어, 출력 결과의 첫 엘리먼트는 5461에서 10922(시작과 끝 슬롯도 포함되는)의 슬롯은 127.0.0.1:7001 노드에 의해 제공되며, 읽기 전용(read-only)부하는 리플리카 노드 127.0.0.1:7004에 접근하여 확장될 수 있다는 것을 말해준다

만약 클러스터 구성이 잘못되어 있으면, `CLUSTER SLOTS`는 전체 16384개의 슬롯을 모두 커버하는 범위를 반환하는 것을 보장하지는 않는다. 그래서 클라이언트는 대상 노드를 NULL로 채워서 슬롯 구성 맵을 초기화해야 하고, 만약 사용자가 할당되지 않은 슬롯에 대해서 커맨드를 실행하려고 하면 에러를 보고해야 한다.

할당되지 않은 슬롯이 발견되면, 호출자에게 에러를 반환하기 전에 클라이언트는 클러스터의 지금 설정이 적절한지를 체크하기 위해서 슬롯 구성을 다시 가져와야 한다. 

### Multiple keys operations

해시 태그를 사용하면, 클라이언트는 다중 키(multi-key) 오퍼레이션을 자유롭게 사용할 수 있다. 예를 들어, 다음의 오퍼레이션은 유효하다.

```
MSET {user:1000}.name Angela {user:1000}.surname White
```

만약 대상 키들이 속한 해시 슬롯의 리샤딩이 진행중이라면, 다중 키 오퍼레이션은 사용할 수 없게 될 수도 있다.

더 구체적으로 말해서, 리샤딩 중에 모두 존재하고 있으며, 여전히 모두 동일한 슬롯(원본 또는 대상 슬롯)으로 해시되는 대상 키들은 다중 키 오퍼레이션은 여전히 가능하다.

존재하지 않거나 리샤딩 중에 원본(source)과 대상(destination) 노드 사이에서 나뉘어진 키들에 대한 오퍼레이션은 `-TRYAGAIN` 에러를 발생시킬 것이다. 클라이언트는 일정 시간 이후에 오퍼레이션을 다시 시도하거나, 에러를 다시 반환할 수 있다.

지정된 해시 슬롯의 마이그레이션이 종료되자마자, 이 해시 슬롯에 대한 모든 다중 키 오퍼레이션은 다시 가능해진다.

### Scaling reads using replica nodes

일반적으로 리플리카 노드는 주어진 커맨드에 포함된 해시 슬롯에 대해 권한이 있는 마스터로 클라이언트를 리다이렉트한다. 그러나 클라이언트는 `READONLY` 커맨드를 사용해서 읽기 요청을 확장하기 위해서 리플리카 노드를 사용할 수 있다.

`READONLY`는 레디스 클러스터 리플리카 노드에게 클라이언트가 오래된 데이터를 읽어도 문제가 없고, 쓰기 관련 커맨드를 실행하는데에는 관심이 없다고 말해준다.

커넥션이 읽기 전용 모드일 때, 클러스터는 리플리카의 마스터 노드에 의해서 제공되지 않는 키들을 포함하는 오퍼레이션에 대해서만 클라이언트에게 리다이렉션을 보낸다. 이것은 다음과 같은 이유로 발생할 수 있다.

1. 클라이언트가 이 리플리카의 마스터 노드에서 제공되지 않는 해시 슬롯에 대한 커맨드를 전송했다.
2. 클러스터가 재구성되고 (예를 들어, 리샤딩), 리플리카 노드는 더 이상 주어진 해시 슬롯에 대한 커맨드를 처리할 수 없다.

이러한 것이 발생하면, 클라이언트는 이전 섹션에서 설명한대로 해시 슬롯 맵을 업데이트 해야 한다.

커넥션의 읽기 전용 상태는 `READWRITE` 커맨드를 이용해서 지울 수 있다.


## Fault Tolerance

### Heartbeat and gossip messages

레디스 클러스터 노드는 계속해서 핑/퐁 패킷을 교환한다. 두 종류의 패킷은 동일한 구조를 가지며, 둘다 중요한 구성 정보를 전달한다. 실제 차이가 나는 것은 메시지 타입의 필드 뿐이다. 핑/퐁 패킷을 합한 것을 *하트 비트 패킷(heartbeat packets)*이라고 한다.

일반적으로 노드는 핑 패킷을 보내고, 수신자가 퐁 패킷을 응답하도록 트리거한다. 그러나 이것이 꼭 사실만은 아니다. 노드가 응답을 트리거링하지 않고, 자신의 구성에 관한 정보를 다른 노드에게 보내기 위해서 퐁 패킷을 보낼 수 있다. 이것은 예를 들어, 새로운 구성 정보를 가능한한 빠르게 브로드캐스트 위한 상황에서 유용하다.

일반적으로 노드는 몇 개의 랜덤한 노드에게 매초 핑을 보내고, 각 노드마다 발송되고 핑 패킷과 수신된 퐁 패킷의 전체 수는 클러스터 내의 노드 수와 관계없이 일정한 양이다.

그러나 모든 노드는 `NODE_TIMEOUT`시간의 절반 이상의 시간 동안, 핑을 보내지 않았거나, 퐁을 수신한 적이 없는 다른 모든 노드에게 핑을 하도록 한다. `NODE_TMEOUT`이 경과되기 전에, 현재 TCP 커넥션에서 문제가 있어서, 접근할 수 없는 노드로 간주하지 않도록 하기 위해서, 다른 노드와 TCP 링크를 재연결하려고 한다.

만약 `NODE_TIMEOUT`가 작은 수치로 설정이 되었고, 노드의 수 (N)이 매우 클 때, 전역적으로 교환되는 메시지의 수는 상당할 수 있는데, 이것은 모든 노드가 `NODE_TIMEOUT`시간의 절반마다 새로운 정보가 없는 다른 모든 노드에게 핑을 보내려고 하기 때문이다.

예를 들어, 100개 노드의 클러스터가 있고, 노드 타임아웃이 60초로 설정이 되었을 때, 각 노드는 매 30초마다 99개의 핑을 보내려고 할 것이고, 전체 핑의 수는 초당 3.3개일 것이다. 100개의 노드를 곱하면, 전체 클러스터에서 초당 330개의 핑이 발생한다.

메시지의 수를 줄일 수 있는 방법이 있지만, 현재 레디스 클러스터 장애 감지에서 사용되는 대역폭에 대해서 보고된 이슈는 없고, 그래서 지금은 명확하고 직접적인 디자인이 사용된다. 심지어 위의 예에서 초당 330개의 교환되는 패킷은 100개의 서로 다른 노드에서 균등하게 나누어지며, 그래서 각 노드가 수신하는 트래픽은 허용 가능하다.

### Heartbeat packet content

핑/퐁 패킷은 모든 타입의 패킷(예를 들어, 페일오버의 투표를 요청하는 등)의 공통적인 헤더와, 핑/퐁 패킷에서 지정하는 특별한 가십 프로토콜 섹션을 포함한다.

공통 헤더는 다음과 같은 정보를 가진다:
참고: https://github.com/redis/redis/blob/f07dedf73facfed5044efaf2a7a780581bf73ffa/src/cluster.h#L272

* 노드 ID, 160비트의 의사난수(pseudorandom) 문자열. 노드가 생성될 때 처음 할당되고, 레디스 클러스터 노드의 운영되는 동안 동일하게 유지된다.
* 전송하는 노드의 `currentEpoch`와 `configEpoch` 필드. 이것은 레디스 클러스터가 분산 알고리즘을 갖추기 위해서 사용된다(이것은 다음 섹션에서 상세하게 설명한다). 만약 노드가 리플리카이면, `configEpoch`는 자신의 마스터 노드의 가장 최근의 `configEpoch`이다.
* 노드 플래그. 노드가 리플리카인지, 마스터인지, 그리고 기타 단일 비트(single-bit)의 노드 정보를 표시한다.
* 전송하는 노드가 담당하는 해시 슬롯의 비트맵. 리플리카인 경우에는 자신의 마스터가 담당하는 슬롯의 비트맵.
* 전송하는 노드의 TCP 기반의 포트. 이것은 레디스가 클라이언트의 커맨드를 반아들이기 위해서 사용하는 포트이다.
* 클러스터 포트. 레디스가 노드간의 커뮤니케이션을 위해서 사용하는 포트이다.
* 전송하는 노드 관점에서의 클러스터의 상태. down 또는 ok.
* 전송하는 노드가 리플리카일 때의 마스터 노드 ID. 

핑/퐁 패킷은 또한 가십 섹션을 포함한다. 이 섹션은 수신자에게 전송하는 노드가 클러스터내의 다른 노드들에 대해서 어떻게 판단하고 있는지에 대한 일람을 전달한다. 가십 섹션은 전송하는 노드가 알고 있는 노드 집합 중에서 몇 개의 랜덤한 노드에 대한 정보만을 포함한다. 가십 섹션에서 언급되는 노드의 수는 클러스터 사이즈에 비례한다.

가십 섹션에 추가되는 모든 노드는 다음의 필드가 보고된다.

* 노드 아이디
* 노드의 IP와 포트
* 노드의 플래그

가십 섹션은 수신하는 노드는 송신하는 노드의 관점에서의 다른 노드들의 상태에 관한 정보를 얻을 수 있다. 이것은 장애를 탐지하고, 클러스터 내의 다른 노드를 발견하는 것에 모두 유용하다.


### Failure detection

레디스 클러스터 실패 탐지(Redis Cluster failure detection)는 과반 수의 노드로부터 어떤 마스터나 리플리카 노드가 더 이상 접근할 수 없는 것을 인식하기 위해서, 그 다음 리플리카를 마스터로 승격시킴으로써 대응한다. 리플리카 프로모션이 불가능하면, 클러스터는 클라이언트로부터의 쿼리 수신을 중지하기 위해서 에러 상태로 전환된다.

이미 언급한대로, 모든 노드는 이미 알고 있는 다른 노드들과 관련된 플래그의 목록을 가진다. 장애 탐지를 위해서 사용되는 `PFAIL`과 `FAIL`이라는 2개의 플래그가 있다. `PFAIL`은 *장애 가능성(Possible failure)*을 의미하며, 승인되지 않은 실패의 타입이다. `FAIL`은 노드가 실패하고 있고, 고정된 시간 내에 과반수 이상의 마스터에 의해서 이 상태가 확인이 되었다는 것을 의미한다.

**PFAIL flag:**

`NODE_TIMEOUT`시간 보다 더 오랜 시간동안 접속할 수 없으면, 어떤 한 노드는 또 다른 노드가 `NODE_TIMEOUT`시간 보다 더 오랜 시간동안 접속할 수 없으면 `PFAIL`로 플래그를 지정한다. 타입에 관계없이 마스터와 리플리카 노드 모두 `PFAIL`로 플래그가 지정될 수 있다.

레디스 클러스터 노드의 접근 불가(non-reachability)의 개념은 `NODE_TIMEOUT`보다 더 긴 시간동안 보류중인 (보냈지만 아직 응답을 아직 받지 못한) **액티브 핑 (active ping)**이 있다라는 것이다. 이 메커니즘이 동작하기 위해서 `NODE_TIMEOUT`은 네트워크 왕복 시간(round trip time)과 비교해서 반드시 더 큰 값이 되어야 한다. 일반적인 오퍼레이션동안 신뢰성을 더하기 위해서, 핑에 대한 응답없이 `NODE_TIMEOUT`의 절반의 시간이 경과하자마자 클러스터 내의 노드는 다른 노드와 다시 연결하려고 시도할 것이다. 이 메커니즘은 커넥션이 살아있는 상태로 유지하려고 하고, 연결이 끊긴 커넥션에 대해서 노드 간에 잘못된 오류를 보고하지 않도록 한다.

**FAIL flag:**

`PFAIL`플래그만으로는 각 노드가 다른 노드들에 대해서 가지는 로컬 정보일 뿐, 리플리카의 승격을 발생시키기에는 충분하지 않다. 어느 한 노드가 다운된 것으로 간주되려면 `PFAIL` 조건은 `FAIL` 조건으로 에스컬레이션되어야 할 필요가 있다.

이 문서의 노드 하트 비트 섹션에서 설명한대로, 모든 노드는 몇 개의 랜덤한 알려진 노드에 대한 상태를 포함해서 가십 메시지를 다른 모든 노드에게 전송한다. 모든 노드는 결국 다른 모든 노드에 대한 노드 플래그의 집합을 받게 된다. 이렇게 모든 노드는 발견한 장애 상태에 대해서 다른 노드로 신호를 보내는 메커니즘을 가진다.

다음의 조건들의 집합을 충족하면, `PFAIL` 상태는 `FAIL`로 에스컬레이션된다.

* 임의의 노드 A는 `PFAIL` 플래그가 설정된 또 다른 노드 B에 대한 정보를 가지고 있다.
* 노드 A는 가십 섹션을 통해서 클러스터 내의 과반수의 마스터의 관점에서의 B의 상태에 관한 정보를 수집했다.
* 과반수의 마스터는 `NODE_TIMEOUT * FAIL_REPORT_VALIDITY_MULT` 시간 내에 `PFAIL`이나 `FAIL`상태를 신호했다. (유효성 계수(validity factor)는 현재의 구현에서 2로 설정되어 있고, 그래서 이것은 단지 `NODE_TIMEOUT`시간의 2배이다.)

위의 조건 모두 참일 때, 노드 A는 아래와 같이 동작할 것이다.

* 노드를 `FAIL`로 표시해둔다.
* (하트 비트 메시지 내에서 `FAIL` 상태가 아닌) `FAIL` 메시지를 접속 가능한 모든 노드에게 전송한다. 

이미 `PFAIL` 상태로 노드가 플래그로 지정되어 있는지 아닌지와 관계없이, `FAIL`메시지는 수신하는 모든 노드가 해당 노드를 `FAIL` 상태로 표시해두도록 한다. 

*`FAIL`플래그는 대부분 단방향이다*. 이것은 어떤 노드가 `PFAIL`에서 `FAIL`로는 바뀔 수 있지만, `FAIL` 플래그는 오직 다음과 같은 상황에서만 해제된다.

* 노드는 이미 접근이 가능하고, 리플리카 노드이다. 이러한 경우 리플리카는 페일오버되지 않기 때문에, `FAIL` 플래그는 해제될 수 있다.
* 노드는 이미 접근이 가능하고, 어떤 슬롯도 처리하지 않는 마스터 노드이다. 이러한 경우 슬롯이 없는 마스터는 클러스터에 실제 참여하고 있지 않고, 클러스터에 참여하기 위해서 구성이 변경되기(configured)를 기다리고 있기 때문에, `FAIL`플래그는 해제될 수 있다.
* 노드는 이미 접근이 가능하고, 마스터 노드이지만, 감지가 가능한 어떤 리플리카의 승격도 없이, 오랜 시간(`NODE_TIMEOUT`을 N번)이 경과되었다.

`PFAIL` -> `FAIL` 변경은 합의의 형태를 사용하지만, 사용되는 합의는 약하다는 점을 알아두면 좋다.

1. 노드들은 일정 시간 동안 다른 노드들의 뷰를 수집하고, 마스터 노드의 과반수가 동의를 할 필요가 있다고 하더라도, 실제로 이것은 다른 노드들로부터 각각 다른 시간에 수집된 상태일 뿐이고, 주어진 시간동안에 마스터의 과반수가 동의한 것을 보장하지도, 요구하지도 않는다. 하지만 오래된 장애 보고는 폐기하므로, 마스터의 과반수에 의해서 시간의 구간 내에 장애가 신호된다.
2. `FAIL`상태를 감지하는 모든 노드는 `FAIL` 메시지를 이용해서 클러스터내의 다른 노드에게 상태를 강제로 적용하지만, 메시지가 모든 노드에 도달할 것이라는 것을 보장할 방법은 없다. 예를 들어, 노드가 `FAIL`상태를 발견할 수 있지만, 네트워크 파티션 때문에 다른 어떤 노드에도 도달할 수 없을 것이다.

그러나 레디스 클러스터 장애 감지는 라이브니스(liveness) 요구사항이 있다. 결국 모든 노드는 주어진 노드의 상태에 관해서 동의해야 한다. 스플릿 브레인으로부터 비롯될 수 있는 2가지의 케이스가 있다. 일부 소수의 노드가 어떤 노드를 `FAIL` 상태로 인지하거나, 또 다른 소수의 노드는 `FAIL` 상태로 인지하지 않는다. 두 가지 경우 모두 결국 클러스터는 주어진 노드에 대해서 한 가지의 관점을 가질 것이다.

**Case 1**: 만약 과반수의 마스터가 어떤 노드를 `FAIL`로 플래그를 지정했다면, 장애 탐지와 그것이 발생시키는 *연쇄 효과(chain effect)* 때문에, 지정된 시간 내에 충분히 장애가 보고될 것이므로, 결국 모든 다른 노드는 그 마스터를 `FAIL`로 플래그를 기록할 것이다. 

**Case 2**: 오직 소수의 마스터만 어떤 노드를 `FAIL`로 플래그를 지정했다면, (모든 노드가 결국 승격에 대해서 알게 하기 위해서 정규적인 알고리즘을 사용하기 때문에) 리플리카 승격은 일어나지 않고, 모든 노드는 위에서 서술한 `FAIL`상태를 해제하는 규칙에 따라 `FAIL` 상태를 해제할 것이다. (예를 들어 `NODE_TIMEOUT`이 N번 경과한 이후에도 승격이 없었던 경우)

**`FAIL`플래그는 리플리카의 승격을 위해 알고리즘의 안전한 부분을 실행하기 위한 트리거로만 사용된다**. 이론적으로 리플리카는 독립적으로 동작하고, 마스터가 접근할 수 없게 되면 리플리카 승격을 시작하고, 만약 마스터가 과반수의 의해서 접근이 가능하다면 다른 마스터들이 승인을 제공하기를 거부할 때까지 기다린다. 그러나 `PFAIL -> FAIL` 상태의 추가적인 복잡성, 약한 합의, 그리고 `FAIL` 메시지가 클러스터의 접근 가능한 부분에 가장 짧은 시간내에 상태를 전파시키는 것은 실질적인 이점이 있다. 이러한 메커니즘 때문에, 만약 클러스터가 에러 상태라면, 일반적으로 모든 노드는 거의 동시에 쓰기를 멈출 것이다. 이것은 레디스 클러스터를 사용하는 어플리케이션의 관점에서 매력적인 기능이다. 또한, 로컬 시스템의 문제(마스터는 다른 마스터 노드의 과반수에 의해 접근이 가능한 것과 달리)때문에 자신의 마스터에 접근할 수가 없는 리플리카가 시작하는 잘못된 투표는 방지된다.


## Configuration handling, propagation, and failovers

Cluster current epoch
---

Redis Cluster uses a concept similar to the Raft algorithm "term". In Redis Cluster the term is called epoch instead, and it is used in order to give incremental versioning to events. When multiple nodes provide conflicting information, it becomes possible for another node to understand which state is the most up to date.

The `currentEpoch` is a 64 bit unsigned number.

At node creation every Redis Cluster node, both replicas and master nodes, set the `currentEpoch` to 0.

Every time a packet is received from another node, if the epoch of the sender (part of the cluster bus messages header) is greater than the local node epoch, the `currentEpoch` is updated to the sender epoch.

Because of these semantics, eventually all the nodes will agree to the greatest `currentEpoch` in the cluster.

This information is used when the state of the cluster is changed and a node seeks agreement in order to perform some action.

Currently this happens only during replica promotion, as described in the next section. Basically the epoch is a logical clock for the cluster and dictates that given information wins over one with a smaller epoch.

Configuration epoch
---

Every master always advertises its `configEpoch` in ping and pong packets along with a bitmap advertising the set of slots it serves.

The `configEpoch` is set to zero in masters when a new node is created.

A new `configEpoch` is created during replica election. replicas trying to replace
failing masters increment their epoch and try to get authorization from
a majority of masters. When a replica is authorized, a new unique `configEpoch`
is created and the replica turns into a master using the new `configEpoch`.

As explained in the next sections the `configEpoch` helps to resolve conflicts when different nodes claim divergent configurations (a condition that may happen because of network partitions and node failures).

replica nodes also advertise the `configEpoch` field in ping and pong packets, but in the case of replicas the field represents the `configEpoch` of its master as of the last time they exchanged packets. This allows other instances to detect when a replica has an old configuration that needs to be updated (master nodes will not grant votes to replicas with an old configuration).

Every time the `configEpoch` changes for some known node, it is permanently stored in the nodes.conf file by all the nodes that receive this information. The same also happens for the `currentEpoch` value. These two variables are guaranteed to be saved and `fsync-ed` to disk when updated before a node continues its operations.

The `configEpoch` values generated using a simple algorithm during failovers
are guaranteed to be new, incremental, and unique.

Replica election and promotion
---

replica election and promotion is handled by replica nodes, with the help of master nodes that vote for the replica to promote.
A replica election happens when a master is in `FAIL` state from the point of view of at least one of its replicas that has the prerequisites in order to become a master.

In order for a replica to promote itself to master, it needs to start an election and win it. All the replicas for a given master can start an election if the master is in `FAIL` state, however only one replica will win the election and promote itself to master.

A replica starts an election when the following conditions are met:

* The replica's master is in `FAIL` state.
* The master was serving a non-zero number of slots.
* The replica replication link was disconnected from the master for no longer than a given amount of time, in order to ensure the promoted replica's data is reasonably fresh. This time is user configurable.

In order to be elected, the first step for a replica is to increment its `currentEpoch` counter, and request votes from master instances.

Votes are requested by the replica by broadcasting a `FAILOVER_AUTH_REQUEST` packet to every master node of the cluster. Then it waits for a maximum time of two times the `NODE_TIMEOUT` for replies to arrive (but always for at least 2 seconds).

Once a master has voted for a given replica, replying positively with a `FAILOVER_AUTH_ACK`, it can no longer vote for another replica of the same master for a period of `NODE_TIMEOUT * 2`. In this period it will not be able to reply to other authorization requests for the same master. This is not needed to guarantee safety, but useful for preventing multiple replicas from getting elected (even if with a different `configEpoch`) at around the same time, which is usually not wanted.

A replica discards any `AUTH_ACK` replies with an epoch that is less than the `currentEpoch` at the time the vote request was sent. This ensures it doesn't count votes intended for a previous election.

Once the replica receives ACKs from the majority of masters, it wins the election.
Otherwise if the majority is not reached within the period of two times `NODE_TIMEOUT` (but always at least 2 seconds), the election is aborted and a new one will be tried again after `NODE_TIMEOUT * 4` (and always at least 4 seconds).

Replica rank
---

As soon as a master is in `FAIL` state, a replica waits a short period of time before trying to get elected. That delay is computed as follows:

    DELAY = 500 milliseconds + random delay between 0 and 500 milliseconds +
            REPLICA_RANK * 1000 milliseconds.

The fixed delay ensures that we wait for the `FAIL` state to propagate across the cluster, otherwise the replica may try to get elected while the masters are still unaware of the `FAIL` state, refusing to grant their vote.

The random delay is used to desynchronize replicas so they're unlikely to start an election at the same time.

The `REPLICA_RANK` is the rank of this replica regarding the amount of replication data it has processed from the master.
Replicas exchange messages when the master is failing in order to establish a (best effort) rank:
the replica with the most updated replication offset is at rank 0, the second most updated at rank 1, and so forth.
In this way the most updated replicas try to get elected before others.

Rank order is not strictly enforced; if a replica of higher rank fails to be
elected, the others will try shortly.

Once a replica wins the election, it obtains a new unique and incremental `configEpoch` which is higher than that of any other existing master. It starts advertising itself as master in ping and pong packets, providing the set of served slots with a `configEpoch` that will win over the past ones.

In order to speedup the reconfiguration of other nodes, a pong packet is broadcast to all the nodes of the cluster. Currently unreachable nodes will eventually be reconfigured when they receive a ping or pong packet from another node or will receive an `UPDATE` packet from another node if the information it publishes via heartbeat packets are detected to be out of date.

The other nodes will detect that there is a new master serving the same slots served by the old master but with a greater `configEpoch`, and will upgrade their configuration. Replicas of the old master (or the failed over master if it rejoins the cluster) will not just upgrade the configuration but will also reconfigure to replicate from the new master. How nodes rejoining the cluster are configured is explained in the next sections.

Masters reply to replica vote request
---

In the previous section it was discussed how replicas try to get elected. This section explains what happens from the point of view of a master that is requested to vote for a given replica.

Masters receive requests for votes in form of `FAILOVER_AUTH_REQUEST` requests from replicas.

For a vote to be granted the following conditions need to be met:

1. A master only votes a single time for a given epoch, and refuses to vote for older epochs: every master has a lastVoteEpoch field and will refuse to vote again as long as the `currentEpoch` in the auth request packet is not greater than the lastVoteEpoch. When a master replies positively to a vote request, the lastVoteEpoch is updated accordingly, and safely stored on disk.
2. A master votes for a replica only if the replica's master is flagged as `FAIL`.
3. Auth requests with a `currentEpoch` that is less than the master `currentEpoch` are ignored. Because of this the master reply will always have the same `currentEpoch` as the auth request. If the same replica asks again to be voted, incrementing the `currentEpoch`, it is guaranteed that an old delayed reply from the master can not be accepted for the new vote.

Example of the issue caused by not using rule number 3:

Master `currentEpoch` is 5, lastVoteEpoch is 1 (this may happen after a few failed elections)

* Replica `currentEpoch` is 3.
* Replica tries to be elected with epoch 4 (3+1), master replies with an ok with `currentEpoch` 5, however the reply is delayed.
* Replica will try to be elected again, at a later time, with epoch 5 (4+1), the delayed reply reaches the replica with `currentEpoch` 5, and is accepted as valid.

4. Masters don't vote for a replica of the same master before `NODE_TIMEOUT * 2` has elapsed if a replica of that master was already voted for. This is not strictly required as it is not possible for two replicas to win the election in the same epoch. However, in practical terms it ensures that when a replica is elected it has plenty of time to inform the other replicas and avoid the possibility that another replica will win a new election, performing an unnecessary second failover.
5. Masters make no effort to select the best replica in any way. If the replica's master is in `FAIL` state and the master did not vote in the current term, a positive vote is granted. The best replica is the most likely to start an election and win it before the other replicas, since it will usually be able to start the voting process earlier because of its *higher rank* as explained in the previous section.
6. When a master refuses to vote for a given replica there is no negative response, the request is simply ignored.
7. Masters don't vote for replicas sending a `configEpoch` that is less than any `configEpoch` in the master table for the slots claimed by the replica. Remember that the replica sends the `configEpoch` of its master, and the bitmap of the slots served by its master. This means that the replica requesting the vote must have a configuration for the slots it wants to failover that is newer or equal the one of the master granting the vote.

Practical example of configuration epoch usefulness during partitions
---

This section illustrates how the epoch concept is used to make the replica promotion process more resistant to partitions.

* A master is no longer reachable indefinitely. The master has three replicas A, B, C.
* Replica A wins the election and is promoted to master.
* A network partition makes A not available for the majority of the cluster.
* Replica B wins the election and is promoted as master.
* A partition makes B not available for the majority of the cluster.
* The previous partition is fixed, and A is available again.

At this point B is down and A is available again with a role of master (actually `UPDATE` messages would reconfigure it promptly, but here we assume all `UPDATE` messages were lost). At the same time, replica C will try to get elected in order to fail over B. This is what happens:

1. C will try to get elected and will succeed, since for the majority of masters its master is actually down. It will obtain a new incremental `configEpoch`.
2. A will not be able to claim to be the master for its hash slots, because the other nodes already have the same hash slots associated with a higher configuration epoch (the one of B) compared to the one published by A.
3. So, all the nodes will upgrade their table to assign the hash slots to C, and the cluster will continue its operations.

As you'll see in the next sections, a stale node rejoining a cluster
will usually get notified as soon as possible about the configuration change
because as soon as it pings any other node, the receiver will detect it
has stale information and will send an `UPDATE` message.

Hash slots configuration propagation
---

An important part of Redis Cluster is the mechanism used to propagate the information about which cluster node is serving a given set of hash slots. This is vital to both the startup of a fresh cluster and the ability to upgrade the configuration after a replica was promoted to serve the slots of its failing master.

The same mechanism allows nodes partitioned away for an indefinite amount of
time to rejoin the cluster in a sensible way.

There are two ways hash slot configurations are propagated:

1. Heartbeat messages. The sender of a ping or pong packet always adds information about the set of hash slots it (or its master, if it is a replica) serves.
2. `UPDATE` messages. Since in every heartbeat packet there is information about the sender `configEpoch` and set of hash slots served, if a receiver of a heartbeat packet finds the sender information is stale, it will send a packet with new information, forcing the stale node to update its info.

The receiver of a heartbeat or `UPDATE` message uses certain simple rules in
order to update its table mapping hash slots to nodes. When a new Redis Cluster node is created, its local hash slot table is simply initialized to `NULL` entries so that each hash slot is not bound or linked to any node. This looks similar to the following:

```
0 -> NULL
1 -> NULL
2 -> NULL
...
16383 -> NULL
```

The first rule followed by a node in order to update its hash slot table is the following:

**Rule 1**: If a hash slot is unassigned (set to `NULL`), and a known node claims it, I'll modify my hash slot table and associate the claimed hash slots to it.

So if we receive a heartbeat from node A claiming to serve hash slots 1 and 2 with a configuration epoch value of 3, the table will be modified to:

```
0 -> NULL
1 -> A [3]
2 -> A [3]
...
16383 -> NULL
```

When a new cluster is created, a system administrator needs to manually assign (using the `CLUSTER ADDSLOTS` command, via the redis-cli command line tool, or by any other means) the slots served by each master node only to the node itself, and the information will rapidly propagate across the cluster.

However this rule is not enough. We know that hash slot mapping can change
during two events:

1. A replica replaces its master during a failover.
2. A slot is resharded from a node to a different one.

For now let's focus on failovers. When a replica fails over its master, it obtains
a configuration epoch which is guaranteed to be greater than the one of its
master (and more generally greater than any other configuration epoch
generated previously). For example node B, which is a replica of A, may failover
A with configuration epoch of 4. It will start to send heartbeat packets
(the first time mass-broadcasting cluster-wide) and because of the following
second rule, receivers will update their hash slot tables:

**Rule 2**: If a hash slot is already assigned, and a known node is advertising it using a `configEpoch` that is greater than the `configEpoch` of the master currently associated with the slot, I'll rebind the hash slot to the new node.

So after receiving messages from B that claim to serve hash slots 1 and 2 with configuration epoch of 4, the receivers will update their table in the following way:

```
0 -> NULL
1 -> B [4]
2 -> B [4]
...
16383 -> NULL
```

Liveness property: because of the second rule, eventually all nodes in the cluster will agree that the owner of a slot is the one with the greatest `configEpoch` among the nodes advertising it.

This mechanism in Redis Cluster is called **last failover wins**.

The same happens during resharding. When a node importing a hash slot completes
the import operation, its configuration epoch is incremented to make sure the
change will be propagated throughout the cluster.

UPDATE messages, a closer look
---

With the previous section in mind, it is easier to see how update messages
work. Node A may rejoin the cluster after some time. It will send heartbeat
packets where it claims it serves hash slots 1 and 2 with configuration epoch
of 3. All the receivers with updated information will instead see that
the same hash slots are associated with node B having an higher configuration
epoch. Because of this they'll send an `UPDATE` message to A with the new
configuration for the slots. A will update its configuration because of the
**rule 2** above.

How nodes rejoin the cluster
---

The same basic mechanism is used when a node rejoins a cluster.
Continuing with the example above, node A will be notified
that hash slots 1 and 2 are now served by B. Assuming that these two were
the only hash slots served by A, the count of hash slots served by A will
drop to 0! So A will **reconfigure to be a replica of the new master**.

The actual rule followed is a bit more complex than this. In general it may
happen that A rejoins after a lot of time, in the meantime it may happen that
hash slots originally served by A are served by multiple nodes, for example
hash slot 1 may be served by B, and hash slot 2 by C.

So the actual *Redis Cluster node role switch rule* is: **A master node will change its configuration to replicate (be a replica of) the node that stole its last hash slot**.

During reconfiguration, eventually the number of served hash slots will drop to zero, and the node will reconfigure accordingly. Note that in the base case this just means that the old master will be a replica of the replica that replaced it after a failover. However in the general form the rule covers all possible cases.

Replicas do exactly the same: they reconfigure to replicate the node that
stole the last hash slot of its former master.

Replica migration
---

Redis Cluster implements a concept called *replica migration* in order to
improve the availability of the system. The idea is that in a cluster with
a master-replica setup, if the map between replicas and masters is fixed
availability is limited over time if multiple independent failures of single
nodes happen.

For example in a cluster where every master has a single replica, the cluster
can continue operations as long as either the master or the replica fail, but not
if both fail the same time. However there is a class of failures that are
the independent failures of single nodes caused by hardware or software issues
that can accumulate over time. For example:

* Master A has a single replica A1.
* Master A fails. A1 is promoted as new master.
* Three hours later A1 fails in an independent manner (unrelated to the failure of A). No other replica is available for promotion since node A is still down. The cluster cannot continue normal operations.

If the map between masters and replicas is fixed, the only way to make the cluster
more resistant to the above scenario is to add replicas to every master, however
this is costly as it requires more instances of Redis to be executed, more
memory, and so forth.

An alternative is to create an asymmetry in the cluster, and let the cluster
layout automatically change over time. For example the cluster may have three
masters A, B, C. A and B have a single replica each, A1 and B1. However the master
C is different and has two replicas: C1 and C2.

Replica migration is the process of automatic reconfiguration of a replica
in order to *migrate* to a master that has no longer coverage (no working
replicas). With replica migration the scenario mentioned above turns into the
following:

* Master A fails. A1 is promoted.
* C2 migrates as replica of A1, that is otherwise not backed by any replica.
* Three hours later A1 fails as well.
* C2 is promoted as new master to replace A1.
* The cluster can continue the operations.

Replica migration algorithm
---

The migration algorithm does not use any form of agreement since the replica
layout in a Redis Cluster is not part of the cluster configuration that needs
to be consistent and/or versioned with config epochs. Instead it uses an
algorithm to avoid mass-migration of replicas when a master is not backed.
The algorithm guarantees that eventually (once the cluster configuration is
stable) every master will be backed by at least one replica.

This is how the algorithm works. To start we need to define what is a
*good replica* in this context: a good replica is a replica not in `FAIL` state
from the point of view of a given node.

The execution of the algorithm is triggered in every replica that detects that
there is at least a single master without good replicas. However among all the
replicas detecting this condition, only a subset should act. This subset is
actually often a single replica unless different replicas have in a given moment
a slightly different view of the failure state of other nodes.

The *acting replica* is the replica among the masters with the maximum number
of attached replicas, that is not in FAIL state and has the smallest node ID.

So for example if there are 10 masters with 1 replica each, and 2 masters with
5 replicas each, the replica that will try to migrate is - among the 2 masters
having 5 replicas - the one with the lowest node ID. Given that no agreement
is used, it is possible that when the cluster configuration is not stable,
a race condition occurs where multiple replicas believe themselves to be
the non-failing replica with the lower node ID (it is unlikely for this to happen
in practice). If this happens, the result is multiple replicas migrating to the
same master, which is harmless. If the race happens in a way that will leave
the ceding master without replicas, as soon as the cluster is stable again
the algorithm will be re-executed again and will migrate a replica back to
the original master.

Eventually every master will be backed by at least one replica. However,
the normal behavior is that a single replica migrates from a master with
multiple replicas to an orphaned master.

The algorithm is controlled by a user-configurable parameter called
`cluster-migration-barrier`: the number of good replicas a master
must be left with before a replica can migrate away. For example, if this
parameter is set to 2, a replica can try to migrate only if its master remains
with two working replicas.

configEpoch conflicts resolution algorithm
---

When new `configEpoch` values are created via replica promotion during
failovers, they are guaranteed to be unique.

However there are two distinct events where new configEpoch values are
created in an unsafe way, just incrementing the local `currentEpoch` of
the local node and hoping there are no conflicts at the same time.
Both the events are system-administrator triggered:

1. `CLUSTER FAILOVER` command with `TAKEOVER` option is able to manually promote a replica node into a master *without the majority of masters being available*. This is useful, for example, in multi data center setups.
2. Migration of slots for cluster rebalancing also generates new configuration epochs inside the local node without agreement for performance reasons.

Specifically, during manual resharding, when a hash slot is migrated from
a node A to a node B, the resharding program will force B to upgrade
its configuration to an epoch which is the greatest found in the cluster,
plus 1 (unless the node is already the one with the greatest configuration
epoch), without requiring agreement from other nodes.
Usually a real world resharding involves moving several hundred hash slots
(especially in small clusters). Requiring an agreement to generate new
configuration epochs during resharding, for each hash slot moved, is
inefficient. Moreover it requires an fsync in each of the cluster nodes
every time in order to store the new configuration. Because of the way it is
performed instead, we only need a new config epoch when the first hash slot is moved,
making it much more efficient in production environments.

However because of the two cases above, it is possible (though unlikely) to end
with multiple nodes having the same configuration epoch. A resharding operation
performed by the system administrator, and a failover happening at the same
time (plus a lot of bad luck) could cause `currentEpoch` collisions if
they are not propagated fast enough.

Moreover, software bugs and filesystem corruptions can also contribute
to multiple nodes having the same configuration epoch.

When masters serving different hash slots have the same `configEpoch`, there
are no issues. It is more important that replicas failing over a master have
unique configuration epochs.

That said, manual interventions or resharding may change the cluster
configuration in different ways. The Redis Cluster main liveness property
requires that slot configurations always converge, so under every circumstance
we really want all the master nodes to have a different `configEpoch`.

In order to enforce this, **a conflict resolution algorithm** is used in the
event that two nodes end up with the same `configEpoch`.

* IF a master node detects another master node is advertising itself with
the same `configEpoch`.
* AND IF the node has a lexicographically smaller Node ID compared to the other node claiming the same `configEpoch`.
* THEN it increments its `currentEpoch` by 1, and uses it as the new `configEpoch`.

If there are any set of nodes with the same `configEpoch`, all the nodes but the one with the greatest Node ID will move forward, guaranteeing that, eventually, every node will pick a unique configEpoch regardless of what happened.

This mechanism also guarantees that after a fresh cluster is created, all
nodes start with a different `configEpoch` (even if this is not actually
used) since `redis-cli` makes sure to use `CONFIG SET-CONFIG-EPOCH` at startup.
However if for some reason a node is left misconfigured, it will update
its configuration to a different configuration epoch automatically.

Node resets
---

Nodes can be software reset (without restarting them) in order to be reused
in a different role or in a different cluster. This is useful in normal
operations, in testing, and in cloud environments where a given node can
be reprovisioned to join a different set of nodes to enlarge or create a new
cluster.

In Redis Cluster nodes are reset using the `CLUSTER RESET` command. The
command is provided in two variants:

* `CLUSTER RESET SOFT`
* `CLUSTER RESET HARD`

The command must be sent directly to the node to reset. If no reset type is
provided, a soft reset is performed.

The following is a list of operations performed by a reset:

1. Soft and hard reset: If the node is a replica, it is turned into a master, and its dataset is discarded. If the node is a master and contains keys the reset operation is aborted.
2. Soft and hard reset: All the slots are released, and the manual failover state is reset.
3. Soft and hard reset: All the other nodes in the nodes table are removed, so the node no longer knows any other node.
4. Hard reset only: `currentEpoch`, `configEpoch`, and `lastVoteEpoch` are set to 0.
5. Hard reset only: the Node ID is changed to a new random ID.

Master nodes with non-empty data sets can't be reset (since normally you want to reshard data to the other nodes). However, under special conditions when this is appropriate (e.g. when a cluster is totally destroyed with the intent of creating a new one), `FLUSHALL` must be executed before proceeding with the reset.

Removing nodes from a cluster
---

It is possible to practically remove a node from an existing cluster by
resharding all its data to other nodes (if it is a master node) and
shutting it down. However, the other nodes will still remember its node
ID and address, and will attempt to connect with it.

For this reason, when a node is removed we want to also remove its entry
from all the other nodes tables. This is accomplished by using the
`CLUSTER FORGET <node-id>` command.

The command does two things:

1. It removes the node with the specified node ID from the nodes table.
2. It sets a 60 second ban which prevents a node with the same node ID from being re-added.

The second operation is needed because Redis Cluster uses gossip in order to auto-discover nodes, so removing the node X from node A, could result in node B gossiping about node X to A again. Because of the 60 second ban, the Redis Cluster administration tools have 60 seconds in order to remove the node from all the nodes, preventing the re-addition of the node due to auto discovery.

Further information is available in the `CLUSTER FORGET` documentation.

Publish/Subscribe
===

In a Redis Cluster clients can subscribe to every node, and can also
publish to every other node. The cluster will make sure that published
messages are forwarded as needed.

The current implementation will simply broadcast each published message
to all other nodes, but at some point this will be optimized either
using Bloom filters or other algorithms.