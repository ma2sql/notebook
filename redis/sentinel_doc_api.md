## Sentinel API
Sentinel은 자신의 상태를 확인하고, 모니터링하는 마스터나 슬레이브의 헬스를 체크하고, 알림이나 여러 변경 이벤틀 수신하기 위한 구독이나, 런타임 중에 구성을 변경하기 위한 여러가지 API를 제공한다.
기본적으로 센티널은 TCP port 26379에서 실행된다(6379는 레디시의 기본 포트). Sentinel은 레디스 프로토콜을 통해서 커맨드를 받아들이기 때문에, redis-cli 또는 다른 종류의 레디스 클라이언트를 이용하여 센티널과 통신할 수 있다.

지금 모니터되고 있는 레디스 인스턴스가 어떠한 상태인지, 센티널 자신이 판단하는 정보, 그리고 또 다른 센티널들은 어떻게 판단하고 있는지 등등을 알아보기 위해 직접 센티널로 명령을 실행해볼 수도 있다. 아니면, `Pub/Sub`를 사용해서, 페일오버나 인스턴스에 에러가 발생하는 등등 매 이벤트가 발생할 때마다, 푸시 형태의 알림을 센티널로부터 받는 것 또한 가능하다.

### Sentinel commands
다음은 일반적으로 사용되는 센티널 관련 커맨드의 목록이다. 센티널의 구성 정보를 변경하기 위한 커맨드는 포함되어 있지 않은데, 이것은 다음 단락에서 살펴볼 것이다.

- **PING** 이 커맨드는 심플하게 **PONG**을 반환한다.
- **SENTINEL masters** 모니터되고 있는 마스터의 목록과 각각의 상태를 보여준다.
- **SENTINEL master <master name>** 지정된 마스터의 상태를 보여준다.
- **SENTINEL slaves <master name>** 지정된 마스터의 리플리카의 목록과 각각의 상태를 보여준다.
- **SENTINEL sentinels <master name>** 지정된 마스터의 센티널 인스턴스의 목록과 각각의 상태를 보여준다.
- **SENTINEL get-master-addr-by-name <master name>** 지정된 마스터의 ip와 port 번호를 반환한다. 만약 이 마스터에 대해 페일오버가 진행되거나 성공적으로 종료될 때에는, 승격되는 리플리카의 ip와 port 번호가 반환된다.
- **SENTINEL reset <pattern>** 지정된 패턴과 매치하는 모든 마스터 정보를 초기화(reset)한다. 패턴은 glob-style로 체크된다. 이 초기화 프로세스는 마스터의 페일오버를 포함한 상태 정보와 마스터와 관련된 모든 리플리카와 센티널 정보를 초기화시킨다.
- **SENTINEL failover <master name>**  만약 마스터가 접근 불가능한 상황이라면, 다른 센티널로부터의 동의 없이도 강제로 페일오버를 발생시킨다. 그렇더라도 새로운 버전의 구성 정보가 발행되므로, 다른 센티널들의 그들의 구성 정보를 업데이트할 수 있다.
- **SENTINEL ckquorum <master name>** 현재의 센티널 구성이 페일오버에 필요한 quorumr과 페일오버의 인가에 필요한 과반수에 도달하고 있는지를 확인한다. 이 커맨드는 모니터링 시스템에서 센티널의 배포 상태가 정상적인지 체크하기 위해 사용된다.
- **SENTINEL flushconfig** 현재의 상태 정보를 포함한 센티널의 구성 정보를 디스크로 재작성하게 한다. 보통 센티널은 구성의 상태에 어떠한 변경이 있을때마다 재작성을 시도한다(이러한 상태는 재시작 할 때마다 디스크로 저장되는 내용 중의 일부). 그러나 때때로 조작 실수나 디스크 페일, 패키지 업그레이드 스크립트나 설정 관리 등의 이유로 구성 파일이 손실될 수 있다. 이러한 경우에는 설정 파일을 강제로 재작성하게 하는 방법이 유용하다. 이 명령은 이전 구성 파일을 완전히 잃어버렸을 때에도 동작한다.


### Reconfiguring Sentinel at Runtime
Redis 2.8.4 버전부터 센티널은 주어진 마스터에 대한 구성 정보의 추가, 삭제, 변경 등을 할 수 있는 API를 제공하기 시작했다. 만약 여러 센티널이 존재할 때, 모든 센티널이 적절하게 동작하기 위해서는 모든 인스턴스에 변경이 함께 적용되어야 한다. 이것은 하나의 센티널에 대해서만 정보를 변경하는 것만으로 자동으로 네트워크를 경유하여 다른 센티널 노드로도 전파시킬 수 없다는 것을 의미한다.

다음은 Sentinel의 구성 정보를 변경하기 위한 `SENTINEL` 의 하위 커맨드 목록이다.

- **SENTINEL MONITOR <name> <ip> <port> <quorum>** 이 커맨드는 센티널에게 지정된 이름, ip, port, quorum을 가진 새로운 마스터에 대한 모니터링을 시작해야한다는 것을 말해준다. sentinel.conf 파일에 직접 구성 정보를 쓰는 것과 동일하다. 차이는 IPv4 또는 IPv6가 형식의 ip가 아닌 hostname 을 지정할 수 없다는 것이다.
- **SENTINEL REMOVE <name>** 지정된 마스터를 삭제하기 위해 사용되는 명령이다. 마스터는 더 이상 모니터되지 않을 것이고, 센티널 내부적인 상태 정보에서도 완전히 삭제될 것이다. 그리고 더 이상 **SENTINEL masters** 등의 명령의 출력 결과에도 표시되지 않을 것이다.
- **SENTINEL SET <name> <option> <value>** `SET` 커맨드는 `CONFIG SET` 커맨드와 매우 유사하며, 지정된 마스터의 설정 파라미터를 변경하기 위해 사용된다. 둘 이상의 옵션/값 쌍이 지정될 수 있다. 모든 설정 파라미터는 sentinel.conf 를 통해서도 설정될 수 있으며, 또한 SET 커맨드로도 가능하다.

다음은 *object-cache* 라고 불리는 마스터의 *down-after-milliseconds* 설정을 변경하기 위한 `SENTINEL SET` 커맨드 사용 예시이다.
```
SENTINEL SET objects-cache-master down-after-milliseconds 1000
```
이미 기술했듯, `SETNINEL SET` 은 sentinel.conf에 지정할 수 있는 모든 파라미터에 대해서 사용될 수 있다. 게다가 `SENTINEL REMOVE`나 `SENTINEL MONITOR`를 이용해서 마스터를 삭제하고 다시 추가하지 않고도 quorum 값만 변경하는 것 또한 가능하다.
```
SENTINEL SET objects-cache-master quorum 5
```
`GET` 커맨드와 동등한 커맨드는 없다는 것에 주의할 것. 이것은 `SENTINEL MASTER` 명령으로 모든 설정 변수를 단순한 포맷 (필드/값 형태의 배열) 형태로 확인하는 것이 가능하기 때문이다.


### Adding or removing Sentinels
이미 배포된 시스템에 새로운 센티널을 추가하는 것은 단순한 프로세스이다. *auto-discover* 매커니즘이 센터널에는 구현되어 있기 때문이다. 필요한 것은 모니터하려는 현재 마스터를 구성 정보에 포함시켜서 센티너를 시작시키는 것 뿐이다. 10초 내에 센티널은 다른 센티널의 목록과 마스터로 연결되어 있는 리플리카 셋 정보를 얻을 수 있다.

*한 번에 여러 센티널을 추가해야할 때에는, 먼저 하나의 센티널을 추가한 다음, 다른 센티널이 새로운 센티널을 발견할 때까지 기다린 다음에, 또 다른 새로운 센티널을 추가하는 식으로 하는 것이 좋다. 되도록 과반수가 달성되는 상태를 유지시켜, 새로운 센티널을 추가하는 과정에서 페일오버가 발생하더라도 오직 하나의 파티션만 존재하도록 보장하기 위함이다.*

네트워크 파티션이 없는 상태에서, 각각 새로운 센티널을 30초 정도의 간격으로 추가하는 것으로 쉽게 달성될 수 있다.

이러한 처리가 마무리된 시점에는 `SENTINEL MASTER mastername` 커맨드를 이용해서 모든 센티널이 마스터를 모니터하고 있는 센티널의 숫자에 대해서 동의하고 있는 상태인지를 확인할 수 있다.

센티널을 삭제하하는 것은 조금 더 복잡하다. 센티널은 이미 한 번 알았던 센티널을 꽤 오랜시간 접속할 수 없는 상태였다고 하더라도 절대로 잊지 않는다. 왜냐하면 페일오브를 인가받고 새로운 구성 번호를 생성하기 위한 과반수 (majority)가 동적으로 변경되는 것을 원치 않기 때문이다. 그래서 센티널을 삭제하기 위해서는 네트워크 파티션이 없는 상태에서 다음과 같은 단계를 수행한다:

1. 삭제하려고 하는 센티널의 프로세스를 멈춘다.
2. `SENTINEL RESET *` 커맨드를 모든 센티널 인스턴스에서 실행한다. (단지 하나의 마스터에 대해서만 리셋을 수행하기위해, `*` 대신 정확한 마스터 명을 기입하는 것도 가능하다.) 순차적으로 30초의 간격을 두고 실행한다.
3. 모든 센티널의 `SENTINEL MASTER mastername` 출력 결과를 확인해서, 모든 센티널이 현재 활성화된 센티널의 수에 대해서 동의하고 있는지를 확인한다. 

### Removing the old master or unreachable replicas
센티널은 주어진 마스터의 리플리카 꽤 오랜시간 접속할 수 없는 상태였다고 하더라도 절대로 잊지 않는다. 네트워크 파티션 또는 실패 이벤트 이후에 반환하는 리플리카를 올바르게 재구성할 수 있어야 하기 때문에 유용하다.

게다가 페일오버 이후에, 페일오버된 마스터는 사실상 새로운 마스터의 리플리카로 다시 추가되는데, 이러한 방법으로 다시 사용가능한 상태가 되자마자 새로운 마스터의 리플리카로 재구성될 수가 있게 된다.

그러나 때때로 리플리카를 영구적으로 센티널에 의해 모니터되는 리플리카의 목록으로부터 삭제하고 싶을 수 있다. (대체로 올드 마스터)

이를 위해서는, `SENTINEL RESET mastername` 커맨드를 모든 센티널에 실행해주어야 한다: 그렇게 하면 모든 센티널은 이 커맨드가 실행된 이후부터 10초 내에 자신의 리플리카 목록을 새롭게 갱신할 것이고, 현재 master의 `INFO` 출력으로부터 올바르게 복제를 하도록 리스팅된 것들만 추가를 할 것이다.

### Pub/Sub Messages
클라이언트는 `SUBSCRIBE` 또는 `PSUBSCRIBE` 명령으로 채널을 구독하고, 지정된 이벤트를 얻기 위해서 센티널을 레디스와 호환되는 **Pub/Sub** 서버로써 사용할 수가 있다(하지만, `PUBLISH`는 할 수 없다.).

채널명은 이벤트의 명칭과 동일하다. 예를 들어, **+sdown** 이라는 채널명은 인스턴스가 SDOWN 상태가 되는 것과 관련한 모든 알림을 받는다. (SDOWN은 쿼리를 실행하는 센티널 기준에서, 모니터 대상 인스턴스로 더 이상 접근이 불가능한 상태가 되었다는 것을 의미).

단순히 모든 메시지를 구독하기 위해서는 `PSUBSCRIBE *`를 실행한다.

다음은 구독 관련 API를 통해 받을 수 있는 채널과 메시지의 목록이다. 첫 단어는 채널명/이벤트명이며, 나머지는 이벤트 데이터의 포맷을 의미한다.

참고: *instance details*이 지정된 것은 대상 인스턴스를 식별하기 위해 제공되는 정보들이라는 것을 의미한다.
```
<instance-type> <name> <ip> <port> @ <master-name> <master-ip> <master-port>
```
마스터를 식별하는 부분은 (@부터 끝까지)는 선택적으로, 인스턴스 자신이 마스터가 아닌 경우에만 표기된다.

- **+reset-master** <instance details> 마스터가 초기화되었다.
- **+slave** <instance details> 새로운 리플리카가 발견되어 추가되었다.
- **+failover-state-reconf-slaves** <instance details> 페일오버에 대한 상태가 *reconf-slaves*로 변경되었다.
- **+failover-detected** <instance details> 페일오버가 다른 센티널 또는 외부 엔티티의해 시작된 페일오버가 발견되었다 (추가된 리플리카가 마스터로 승격되는).
- **+slave-reconf-sent** <instance details> 새로운 리플리카에 대한 재구성을 위해서, 리더를 맡은 센티널이 `SLAVEOF` 커맨드를 그 인스턴스로 보낸다.
- **+slave-reconf-inprog** <instance details> 재구성되고 있는 리플리카는 새로운 마스터의 ip:port에 대한 리플리카로 표기되고 있지만, 실제로 아직 동기화가 완료되지 않고 처리중인 상태이다.
- **+slave-reconf-done** <instance details> 이제 리플리카의 새로운 마스터에 대한 동기화가 완료되었다.
- **-dup-sentinel** <instance details> 지정된 마스터에 대한 하나 또는 그 이상의 센티널 이 중복되어 삭제되었다. (이것은 센티널 인스턴스가 재시작되었을 때 발생한다.)
- **+sentinel** <instance details> 이 마스터에 대한 새로운 센티널이 발견되었고, 추가되었다.
- **+sdown** <instance details> 지정된 인스턴스가 SDOWN(Subjectively Down) 상태가 되었다.
- **-sdown** <instance details> 지정된 인스턴스의 SDOWN(Subjectively Down) 상태가 해제되었다.
- **+odown** <instance details> 지정된 인스턴스가 ODOWN(Objectively Down) 상태가 되었다.
- **-odown** <instance details> 지정된 인스턴스의 ODOWN(Objectively Down) 상태가 해제되었다.
- **+new-epoch** <instance details> 현재의 epoch값이 업데이트되었다.
- **+try-failover** <instance details> 진행중인 새로운 페일오버는 현재 과반수로 선출되기를 기다리고 있다.
- **+elected-leader** <instance details> 지정된 epoch에서 선출이 되었고, 페일오버를 할 수 있는 상태가 되었다.
- **+failover-state-select-slave** <instance details> 새로운 페일오버 상태가 *select-slave*이다: 승격시키기에 적절한 리플리카를 찾는 중이다.
- **no-good-slave** <instance details> 승격시킬 수 있는 *good replica*가 없다. 아마 일정 시간이 지나고 난 이후에 다시 시도하겠지만, 상황은 달라질 것이고, 이러한 경우에 모든 페일오버 조치는 중단될 것이다.
- **selected-slave** <instance details> 승격시킬 `good replica`를 발견했다.
- **failover-state-send-slaveof-noone** <instance details> 승격된 리플리카를 마스터로 재구성하도록 시도하고, 완료되기를 기다린다.
- **failover-end-for-timeout** <instance details> 타임아웃에 의해서 페일오버가 중단되었지만, 리플리카들은 결국 새로운 마스터로 어떻게든 복제되도록 구성될 것이다.
- **failover-end** <instance details> 페일오버가 성공과 함께 종료되었다. 모든 리플리카들이 새로운 마스터로 복제하도록 구성된 것으로 보이기 시작한다.
- **switch-master** <master name> <oldip> <oldport> <newip> <newport> 마스터의 새로운 IP와 주소는 구성이 변경된 이후에 지정된 것이다. 이것은 대부분의 외부 유저들이 관심을 가질만한 정보이다.
- **+tilt** *Tilt* 모드가 되었다.
- **-tilt** *Tilt* 모드가 해제되었다.

### Handling of -BUSY state
루아(Lua) 스크립트가 설정된 타임아웃보다 더 오랜 시간동안 실행되고 있을 때, 레디스 인스턴스로부터 `-BUSY` 에러가 반환된다. 페일오버가 발생하기 전에 이것이 발생하면, 센티널은 `SCRIPT KILL` 커맨드를 보낼 것이다. 그리고 이 커맨드는 스크립트가 오직 *read-only*인 경우에만 성공할 것이다.

만얀 이 커맨드 실행 이후에도 인스턴스가 여전히 에러를 발생하고 있다면, 결국 페일오버가 발생하게 될 것이다.

### Replicas priority
레디스 인스턴스는 *replica-priority*라는 설정 변수를 가지고 있다. 이 정보는 레디스 리플리카 인스턴스의 `INFO` 커맨드의 출력 값으로 노출되며, 센티널은 마스터로 페일오버 시킬 리플리카를 선택하기 위해 이 정보를 사용할 수 있다.

1. 만약 *replica-priority*를 0으로 설정하면, 이 리플리카는 절대 마스터로 승격될 수 없다.
2. 더 작은 *replica-priority* 값을 가진 리플리카들이 센티널에 의해 선택되어질 가능성이 높다.

예를 들어, 현재의 마스터와 동일한 데이터 센터내에 위치하는 리플리카 S1이 있고, 또 다른 데이터 센터에 위치하는 리플리카 S2가 있다. S1의 priority는 10, 그리고 S2는 priority가 100이라고 할 때, 만약 마스터에서 페일이 발생하고 S1, S2 둘 다 사용 가능한 상황이라면 S1이 선택될 것이다.

리플리카가 선택되는 방법에 대한 더 많은 정보는 이 문서의 *replica selection and priority* 섹션을 참고할 것.

### Sentinel and Redis authentication
보안 조치로써, 마스터가 클라이언트에게 패스워드를 요구하도록 구성되었다면, 리플리카 역시 마스터와의 인증과 비동기 리플리케이션 프로토콜에 사용되는 *master-replica* 커넥션을 생성하기 위해서, 이 패스워드가 무엇인지 알아야 할 필요가 있다.

이것은 다음의 구성 지시로 달성될 수 있다.
- **requirepass** 마스터에서 패스워드를 설정하여, 인증되지 않은 클라이언트로부터의 요청을 처리하지 않는 것을 확실히 하기 위한 옵션
- **masterauth** 리플리카가 마스터의 데이터를 문제없이 리플리케이션 하기 위해, 마스터와의 인증에 필요한 패스워드

만약 센티널이 사용되고, 단일 마스터만 있는 것이 아니라면, 페일오버 후에 리플리카는 마스터의 롤을 수행할 것이고, 오래된 마스터는 새로운 마스터의 리플리카로 재구성될 수 있다. 그렇기 때문에 마스터들과 리플리카들 모두에 대해서 위의 지시들을 설정할 필요가 있다.

동일한 데이터에 접근이 가능한 리플리카들을 가진 특정 마스터의 데이터에 대해서만 보호해야하는 것이 아니라면, 이것은 보통 합리적이다.  
그러나 인증없이도 접근이 필요한 리플리카가 필요한 경우처럼 일반적이지 않은 경우가 있을 수 있는데, 이러한 경우에는 *replica-priority*를 0으로 설정해서 이 리플리카가 마스터가 되는 것을 막고, 이 리플리카에 대해서는 **requirepass**없이, 오직 **masterauth** 지시만 설정해서, 인증없는 클라이언트가 데이터를 읽을 수 있도록 하게 할 수 있다.

센티널들이 **requirepass**가 설정된 레디스 서버 인스턴스로 연결하기 위해서, 센티널은 아래와 같은 포맷으로 `sentinel auth-pass` 지시를 반드시 구성에 포함시켜야 한다.
```
sentinel auth-pass <master-group-name> <pass>
```

### Configuring Sentinel instances with authentication
센티널 인스턴스에도 `AUTH` 커맨드로 통해 클라이언트에게 인증을 요구하도록 패스워드를 설정하는 것이 가능하다. *다만 이 기능은 오직 5.0.1 버전부터 사용이 가능하다.*
그렇게 하기 위해서는 다음과 같은 구성 지시를 모든 센티널 인스턴스에 추가하면 된다:
```
requirepass "your_password_here"
```
이렇게 설정했을 때, 센티널은 다음의 두 가지 작업을 수행한다.
1. 센티널로 명령을 보내려는 클라이언트로부터 패스워드를 요구한다. 이것은 일반적으로 레디스에서 구성 지시가 동작하는 방식이므로 분명하다.
2. 또한, 로컬 센티널에 접근하기 위해 설정되는 동일한 패스워드는 다른 센티널들로 접근하기 위해서도 사용될 것이다.

이것은 **모든 센티널에 동일한 requirepass를 설정해야한다는 것을 의미**한다. 이러한 방법으로 모든 센티널은 다른 센티널들과 별도의 설정없이, 각각에 지정된 센티널 패스워드를 통해서 다른 센티널로 접근할 수가 있는데, 이것은 실현되기 매우 어렵다.(?)

이 설정을 사용하기에 앞서, 현재 사용하고 있는 클라이언트 라이브러리가 센티널 인스턴스에 대해 `AUTH` 커맨드를 사용할 수 있는지 확인해야 한다.

### Sentinel clients implementation
모든 요청이 새로운 마스터를 향하도록 하는 (VIP 또는 이와 유사한) 시스템이 별도로 구성되어 있지 않는 한, 명시적인 클라이언트의 지원이 필요하다. 클라이언트 라이브러리의 구현에 관련한 주제에 대해서는 [Sentinel clients guidelines](https://redis.io/topics/sentinel-clients) 문서에서 다룬다.