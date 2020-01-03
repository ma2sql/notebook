---
tags: [redis, stream]
---

## Streams Basics

- 스트림은 기본적으로 append only 자료구조
- 기본적으로 데이터를 쓰기 위한 명령은 `XADD` (엔트리 추가)
- 스트림의 엔트리는 키-값 의 형태

```
# XADD key ID field value [field value ...]
> XADD mystream * sensor-id 1234 temperature 19.8
1518951480106-0
```
- `XADD`는 키와 함께 ID, 그리고 field-value의 엔트리 값을 전달해야한다.
- 위의 예제에서는 키의 ID로서 `*`를 전달하였는데, 이것은 레디스 서버에게 엔트리 ID의 생성을 맡기는 것이다.
- ID는 로그 파일의 라인 넘버 또는 파일의 오프셋과 같은 역할을 한다.
- `XLEN` 커맨드로는 스트림의 길이를 알 수 있다.
```
> XLEN mystream
(integer) 1
```

### Entry IDs
- 각각의 엔트리를 명확히 구분하는 ID로, 다음과 같이 밀리초 단위의 시간과 시퀀스 번호로 이루어진다.
```
<millisecondsTime>-<sequenceNumber>
```
- 밀리초 단위의 시간은 로컬 레디스가 생성하는 것으로, 이전 엔트리보다 작을 가능성도 있다.
- 이 때는 이전 시간을 사용하고 시퀀스 번호를 하나 더 증가시킨다.
- 시퀀스 번호는 64bit로, 실제로 동일한 밀리초 내애서는 거의 무한한 값이다.
- ID값으로 시간을 쓰는 것이 이상할수도 있는데, ID를 기준으로하는 범위 쿼리를 사용 가능토록 하기 위함이다. `XRANGE`
- 사용자의 필요에 의해 자신만의 포맷의 ID를 부여할 수도 있다.
```
> XADD somestream 0-1 field value
0-1
> XADD somestream 0-2 foo bar
0-2
```
- 이러한 경우에, ID값이 기존의 값과 동일하거나 더 작을 수는 없다.
```
> XADD somestream 0-1 foo bar
(error) ERR The ID specified in XADD is equal or smaller than the target stream top item
```

## Getting data from Streams

## Listening for new items with XREAD
1. 스트림에 새로운 엔트리가 추가된 것을 하나 이상의 컨슈머는 전달받을 수 있다.
    - LIST의 Blocking API와 비슷하나, 하나 이상의 컨슈머로의 통지는 Pub/Sub과 유사하다.
2. 모든 메시지가 스트림별로 개별적으로 쌓이기 때문에, 각각의 컨슈머는 자신이 기억하는 ID를 기준으로 새로운 ID를 판별해낼 수 있다.
3. 스트림 컨슈머 그룹 (Streams Consumer Groups)은 동일한 스트림에 대해 각각 다른 컨슈머 그룹을 가지는 것이 가능하다.

`XREAD`가 이러한 것들을 도와준다.

```
> XREAD COUNT 2 STREAMS mystream 0
1) 1) "mystream"
   2) 1) 1) 1519073278252-0
         2) 1) "foo"
            2) "value_1"
      2) 1) 1519073279157-0
         2) 1) "foo"
            2) "value_2"
```

위는 `XREAD`의 논블로킹(non-blocking)의 형태이다. `COUNT` 옵션은 필수가 아니지만, `STREAMS` 옵션이 필수이다. 이 옵션에는 키의 목록, 그리고 키와 연관이 있는 ID를 함께 지정해야한다. 각각의 ID값은 호출하는 컨슈머가 각각의 스트림에 대해 이미 볼 수 있는 ID의 최대값을 지정해야 한다. 그렇게하면 이 커맨드는 지정된 ID보다 큰 ID의 메시지에 대해서만 클라이언트에게 제공하게 된다.

위 커맨드에서는 `STREAMS mystream 0`을 지정했고, 스트림 `mystream` 내에서 `0-0`보다 큰 ID의 모든 메시지를 얻을 수 있다. 위의 예제에서 볼 수 있듯, 커맨드는 키 네임을 함께 반환한다. 왜냐하면 실제 이 커맨드에 동시에 여러 스트림으로부터 읽기 위해 하나 이상의 키를 지정하여 호출하는 것이 가능하기 때문이다. 예를 들면, 이렇게 지정하는 것이 가능하다. `STREAMS mystream otherstream 0 0`. `STREAMS` 옵션 뒤에 키 네임들과 그 이후에 ID 목록을 지정해야하는 것을 참고하세요. 이러한 이유로 `STREAMS` 옵션은 항상 마지막에 지정해야합니다.

`XREAD`가 한 번에 여러 스트림에 동시에 접근하고, 단지 새로운 메시지를 얻기 위해, 소유한 마지막 ID를 지정할 수 있다는 것 이외에는, 이 심플한 형식은 `XRANGE`와 비교해서 특별하게 차이가 있는 무언가를 하고 있지는 않다. 하지만 흥미로운 부분은 우리는 `XREAD`에 `BLOCK` 인수를 지정해서 쉽게 블로킹 커맨드로 사용할 수 있는 것이다.

```
> XREAD BLOCK 0 STREAMS mystream $
```

위의 예에서, **COUNT**를 제외하는 것 외에도 **BLOCK** 옵션을 타임아웃 0(절대 타임아웃이 되지 않는)과 함께 지정했다. `mystream` 에 대해 일반적인 ID를 전달하는 대신, 특별한 ID인 `$`를 전달했다. 이것은 **XREAD**가 마지막 ID로 `mystream`에 저장되어 있는 값중 가장 큰 ID값을 사용한다는 것을 의미한다. 그리하여 리스닝을 시작하는 시점에서부터 오직 새로운 메시지만 받게 된다. 이것은 유닉스 커맨드인 `tail -f`와 어떤면에서는 비슷한 방식이다.

**BLOCK** 옵션을 사용할 때, 반드시 `$`를 지정할 필요는 없고, 다른 유효한 ID를 지정할 수도 있다. 만약 커맨드가 사용자의 요청을 블로킹 없이 처리할 수가 있다면 그렇게 할 것이고, 아니면 블로킹을 하게 될 것이다. 일반적으로 우리가 스트림을 새로운 엔트리로부터 스트림을 소비하려고 할 때, ID를 `$`로 지정하여 시작하고, 그리고 나서 마지막으로 받은 메시지의 ID를 이용해서 계속해서 다음 요청 등을 실행할 수 있다.

**XREAD**의 블로킹 폼은 단지 키를 여럿 지정함으로써, 여러 스트림으로부터 읽어들이는 것 또한 가능하다. 지정한 ID보다 큰 엘레먼트를 가진 스트림이 적어도 하나가 있어, 요청을 동기식으로 처리할 수 있다면, 결과와 함께 반환될 것이다. 그렇지 않으면, 커맨드는 블로킹될 것이고, (지정된 ID에 따라서) 새로운 데이터를 얻은 첫 스트림의 아이템을 반환할 것이다. 

리스트의 블로킹 오퍼레이션과 마찬가지로, 의미론적으로 FIFO 스타일이기 때문에, 블로킹 스트림은 읽기는 데이터를 기다리는 클라이언트의 관점에서는 공정하다. 주어진 스트림에 대해 블록된 첫 클라이언트는 새로운 아이템이 사용 가능할 때 차단이 해제되는 첫 번째 클라이언트가 된다.

**XREAD**에는 **COUNT**와 **BLOCK**외의 다른 옵션은 없고, 컨슈머를 하나 또는 그 이상의 스트림으로 연결하기 위한 특정한 목적을 가진 매우 기본적인 커맨드다. 스트림을 소비하기 위한 좀 더 강력한 기능은 컨슈머 그룹 API (Consumer Groups API)를 사용함으로써 가능해지는데, 컨슈머 그룹을 통한 읽기는 **XREADGROUP**이라는 또 다른 커맨드에 의해 실현될 수 있다. 이것에 대한 가이드는 다음 섹션에서 다룬다.


## Consumer groups

지금 하고 있는 일이 서로 다른 클라이언트로부터 동일한 스트림을 소비하는 것일때, 그러면 **XREAD** N 클라인트로 팬아웃(fan-out)하는 방법을 이미 제공하고 있고, 읽기 확장성을 제공하기 위해 잠재적으로는 슬레이브를 이용할 수도 있다. 하지만 특정한 상황에서 우리가 원하는 것은 다수의 클라이언트에게 동일한 스트림의 메시지를 제공하는 것이 아니라, 동일한 스트림으로부터 메세지의 **각각 다른 서브셋**을 다수의 클라이언트에게 제공하는 것이다. 이것이 유용한 분명한 경우는 메시지의 처리가 느린 경우이다. 스트림의 각각 다른 부분을 전달받을 수 있는 워커를 N개 가질 수 있다는 것은, 좀 더 많은 일을 할 수 있도록 준비가 된 워커로 메시지를 라우팅함으로써, 메시지의 처리를 확장할 수 있도록 해준다.

현실적으로, 우리가 C1, C2, C3 3개의 컨슈머를 가지고 있고, 스트림 하나는 1,2,3,4,5,6,7의 메시지를 가지고 있다고 상상해보자. 우리가 원하는 것은 다음의 다이어그램과 같이 메시지를 처리하는 것이다.

```
1 -> C1
2 -> C2
3 -> C3
4 -> C1
5 -> C2
6 -> C3
7 -> C1
```

이러한 효과를 얻기 위해서, 레디스는 *consumer groups*라고 불리는 컨셉을 사용한다. 레디스 컨슈머 그룹은 구현의 관점에서 Kafka(TM)의 컨슈머 그룹과 관련이 없다는 것을 이해하는 것은 매우 중요하지만, 구현하는 컨셉의 관점에서는 유사하다. 따라서, 그러한 아이디어를 대중화한 소프트웨어 프로덕트와 비교되는 이 용어를 바꾸지 않기로 했다.

컨슈머 그룹은 스트림으로 데이터를 얻어, 실제 여러 컨슈머에게 전달하는 가상의 컨슈머? (*pseudo consumer*)와 같고, 특정한 보장을 제공한다.

1. 각 메시지는 각각의 컨슈머로 서빙되며, 동일한 메시지가 여러 컨슈머로 전달될 가능성은 없다.
2. 컨슈머는 하나의 컨슈머 그룹 내에서 이름으로 식별되며, 이 이름은 대소문자를 구분하는 문자열로, 컨슈머를 구현하는 클라이언트는 반드시 이름을 지정해야한다. 이것은 심지어 커넥션이 끊긴 이후에도, 스트림 컨슈머 그룹은 모든 상태를 유지, 때문에 클라이트는 다시 동일한 컨슈머가 될 수 있다. 그러나, 물론 이것은 클라이언트가 제공하는 유니크한 식별자에 달려있다.
3. 각 컨슈머는 *first ID never consumed* 라는 컨셉을 가지고 있는데, 컨슈머가 새로운 메시지를 요청할 때, 이전에 결코 전달된 적이 없이 메시지를 전달한다.
4. 메시지를 소비하는 것은 하지만 지정된 커맨드를 이용한 명시적인 응답을 필요로 한다. 말하자면: 이 메시지는 올바르게 처리되었기 때문에, 컨슈머 그룹에서 제거되어도 된다.
5. 컨슈머 그룹은 현재 보류중인 모든 메시지를 추적한다. 메시지가 컨슈머 그룹내의 어떤 컨슈머로 전달이 되었지만, 아직 처리되었다는 응답을 받지 못한 것을 의미한다. 이러한 기능 덕분에 스트림의 메시지 히스토리에 접근할 때, 각 컨슈머는 *오직 자신에게 전달된 메시지만 볼 수 있다.*

어떤 면에서, 컨슈머 그룹은 스트림에 대한 상태 총합의 일부로써 생각해볼 수 있다:

```
+----------------------------------------+
| consumer_group_name: mygroup           |
| consumer_group_stream: somekey         |
| last_delivered_id: 1292309234234-92    |
|                                        |
| consumers:                             |
|    "consumer-1" with pending messages  |
|       1292309234234-4                  |
|       1292309234232-8                  |
|    "consumer-42" with pending messages |
|       ... (and so forth)               |
+----------------------------------------+
```

이러한 관점으로부터 본다면, 컨슈머 그룹이 무엇을 하는지, 어떻게 보류중인 메시지의 히스토리를 컨슈머에게 전달할 수 있는지, 그리고 어떠한 새로운 메시지를 요청하는 컨슈머가 `last_delivered_id` 보다 큰 메시지 ID만을 전달받을 수 있는지, 쉽게 이해할 수 있다. 동시에 레디스의 스트림에 대한 보조적인 자료구조의 측면으로 컨슈머 그룹을 본다면, 하나의 스트림이 여러 컨슈머 그룹을 가질 수 있고, 각각의 컨슈머 그룹을 가질 수 있는 것은 분명하다. 실제로 심지어  동일한 스트림에 대해 컨슈머 그룹없이  **XREAD**를 이용하여 데이터를 읽는 클라이언트와 각각의 컨슈머 그룹에서 **XREADGROUP**을 이용하여 데이터를 읽는 클라이언트를 존재하는 것도 가능하다.

이제, 다음과 같은 기본적인 컨슈머 그룹 커맨드들을 살펴보자.

* **XGROUP**은 컨슈머 그룹을 생성하고, 삭제하고, 관리하는데 사용되는 명령이다.
* **XREADGROUP**은 컨슈머 그룹을 통해 데이터를 읽기 위해 사용되는 명령이다.
* **XACK**은 보류중인 메시지를 올바르게 처리된 것으로 표시할 수 있는 커맨드다.

## Creating a consumer group

만약 `mystream` 이라는 스트림 데이터 타입의 키가 이미 레디스에 저장되어 있다고 할 때, 그룹을 만들기 위해서는 아래와 같이 할 필요가 있다.

```
> XGROUP CREATE mystream mygroup $
OK
```

위의 커맨드에서 보듯이, 컨슈머 그룹을 만들 때에는 ID를 반드시 지정해야하고, 예제에서는 `$`를 지정했다. 이것이 필요한 이유는 각기 다른 상태의 컨슈머 그룹은 첫 번째 컨슈머가 접속할 때, 다음에 제공되어야하는 메시지가 무엇인지에 대한 인식이 있어야하기 때문이고, 그 인식은 그룹이 만들어졌을 때, 현재의 *last message ID*가 무엇인지에 대한 것이다. `$`를 지정한다면, 그때부터 스트림 내에 도착하는 새로운 메시지는 그룹 내의 컨슈머들에게 전달될 것이다. 대신 `0`을 지정한다면, 컨슈머 그룹은 스트림 히스토리의 시작부터 *모든* 메시지를 소비할 것이다. 물론, 다른 유효한 ID를 지정하는 것 또한 가능하다. 알아야할 것은 컨슈머 그룹은 지정된 ID보다 큰 값의 메시지들을 전달하기 시작한다는 것이다. `$`는 현재 스트림 내에서 가장 큰 ID 값을 지정한다는 의미이기 때문에, `$`는 오직 새로운 메시지만 소비하는 효과가 있다.

`XGROUP CREATE`는 마지막 인수로 `MKSTREAM`를 사용해서, 존재하지 않는 스트림을 자동으로 생성하게 하는 것 또한 지원한다.

```
> XGROUP CREATE newstream mygroup $ MKSTREAM
OK
```

이제 컨슈머 그룹이 생성되었기 때문에, 우리는 즉시 컨슈머 그룹에 **XREADGROUP** 커맨드를 사용해서 메시지를 읽어볼 수 있다. 시스템이 Alice와 Bob으로 각각 다른 메시지를 어떻게 반환하는지 알아보기 위해, Alice와 Bob이라고 불리는 컨슈머들로부터 데이터를 읽을 것이다.

**XREADGROUP**은 **XREAD**와 매우 유사하고, 동일한 **BLOCK** 옵션을 제공하는데, 이 부분을 제외하면 동기식 커맨드이다. 그러나 반드시 지정되어야하는 *필수(manatory)* 옵션인 **GROUP**이 있는데, 이 옵션은 컨슈머 그룹의 이름과 읽기를 시도하는 컨슈머의 이름, 2개의 인수를 지정한다. 그리고 **XREAD**와 동일한 **COUNT** 옵션 또한 지원한다.

스트림으로부터 데이터를 읽기 전에, 몇가지 메시지를 입력해보자.

```
> XADD mystream * message apple
1526569495631-0
> XADD mystream * message orange
1526569498055-0
> XADD mystream * message strawberry
1526569506935-0
> XADD mystream * message apricot
1526569535168-0
> XADD mystream * message banana
1526569544280-0
```
참고: *여기의 message는 필드명이고, 과일 이름은 관련된 값이다. 스트림 아이템은 작은 딕셔너리라는 것을 기억하자.*

그렇다면 이제 컨슈머 그룹을 이용해서 무언가를 읽어보자.

```
> XREADGROUP GROUP mygroup Alice COUNT 1 STREAMS mystream >
1) 1) "mystream"
   2) 1) 1) 1526569495631-0
         2) 1) "message"
            2) "apple"
```

**XREADGROUP**의 응답은 **XREAD**의 응답과 동일하다. 그러나 위에서는 `GROUP <group-name> <consumer-name>`이 제공되었는데, 이것은 컨슈머 그룹 `mygroup`을 이용해서 스트림으로부터 데이터를 읽기를 원하고, 컨슈머명은 `Alice`라고 명시했다. 컨슈머가 컨슈머 그룹과 함께 오퍼레이션을 수행하려고 할 때마다, 반드시 그룹 내에서 유니크하게 식별할 수 있는 이름을 지정해야한다.

위의 커맨드 라인에는 또다른 아주 중요한 세부 사항이 있는데, **STREAMS**라는 필수 옵션에 뒤따르는 키 `mystream`에 대해 요청된 ID가 특별한 ID 값인 `>`로 지정된 것이다. 이 특별한 ID는 오직 컨슈머 그룹의 문맥 내에서만 유효하고, 그 의미는 **메시지가 아직까지 결코 다른 컨슈머로 전달된 적이 없다.**이다.

이것은 거의 항상 당신이 원한 것일텐데, 하지만 `0`이나 다른 유효한 ID와 같이 실제 존재하는 ID로 지정하는 것 또한 가능하다. 이러한 경우에 발생하는 것은 우리가 요청한 **XREADGROUP**이 단지 보류중인 메시지의 히스토리를 우리에게 제공하는 것 뿐이고, 이러한 경우에 우리는 그룹 내에서 새로운 메시지를 절대 볼 수 없을 것이다. 그래서 기본적으로 **XREADGROUP**는 우리가 지정한 ID에 기반으로 다음과 같이 동작한다.

* 만약 ID를 특별한 값인 `>`로 지정하면, 커맨드는 이전까지 다른 컨슈머로 절대 전달하지 않은 새로운 메시지만을 반환할 것이고, 부수적으로는 컨슈머 그룹의 *last ID*를 업데이트할 것이다.
* 만약 ID를 유효한 숫자 ID로 지정하면, 커맨드는 우리가 *보류중인 메시지의 히스토리(history of pending messages)*로 접근하게 할 것이다. 그것은, 특정한 컨슈머(전달한 이름에 의해 식별될 수 있는)로 전달된 적이 있는 메시지의 집합이고, 아직까지 **XACK**로 수신에 대한 통지가 없었던 메시지이다.

우리는 **COUNT** 옵션 없이 ID를 0으로 지정해서 이 동작을 즉시 테스트해볼 수 있다. 우리는 오직 보류중인 메시지만을 볼 수 있고, 그것은 사과(apple)에 관한 것이다.

```
> XREADGROUP GROUP mygroup Alice STREAMS mystream 0
1) 1) "mystream"
   2) 1) 1) 1526569495631-0
         2) 1) "message"
            2) "apple"
```

그러나, 만약 우리가 이 메시지가 처리되었다고 통지를 한다면, 더 이상 보류 메시지 히스토리의 일부분이 아니게 되고, 그렇기 때문에 시스템은 더 이상 어떠한 것도 보고하지 않는다.

```
> XACK mystream mygroup 1526569495631-0
(integer) 1
> XREADGROUP GROUP mygroup Alice STREAMS mystream 0
1) 1) "mystream"
   2) (empty list or set)
```

아직 **XACK**가 어떻게 동작하는지 모르더라도, 걱정할 필요가 없다. 컨셉은 처리된 메시지가 더 이상 우리가 접근할 수 있는 히스토리의 일부분이 아니라는 것이다.

이제, Bob으로 무언가를 읽을 차례이다.

```
> XREADGROUP GROUP mygroup Bob COUNT 2 STREAMS mystream >
1) 1) "mystream"
   2) 1) 1) 1526569498055-0
         2) 1) "message"
            2) "orange"
      2) 1) 1526569506935-0
         2) 1) "message"
            2) "strawberry"
```

Bob은 최대 2개의 메시지를 요청했고, 동일하게 `mygroup`을 통해서 데이터를 읽는다. 그렇게 해서 발생하는 일은 Redis가 새로운 메시지를 반환하는 것이다. 위에서 볼 수 있는 것처럼 "apple" 메시지는 전달되지 않으며, 이미 Alice에게 전달된 적이 있기 때문이다. 그래서 Bob은 orange와 strawberry 등등을 얻을 수 있다.

이러한 방법으로 그룹 내의 Alice, Bob, 그리고 다른 컨슈머들은 동일한 스트림으로부터 각각 다른 메시지를 읽을 수 있고, 아직 처리되지 않은 메시지의 히스토리를 읽을 수도 있으며, 또는 메시지를 처리된 것으로 표시할 수 있다. 이것은 스트림으로부터 메시지를 소비하기 위한 별도의 토폴로지와 시맨틱(의미 체계)를 만들 수 있게 한다.

명심해야할 몇 가지가 있다:

* 컨슈머는 처음 언급될 때 자동으로 생성되어, 명시적으로 생성할 필요는 없다.
* **XREADGROUP**으로도 동시에 여러 키를 읽을 수 있지만, 이 기능을 사용하려면, 매 스트림마다 동일한 이름으로 컨슈머 그룹을 만들 필요가 있다. 이것은 보통 필요하지 않지만, 이러한 기능이 기술적으로는 가능하다는 것 정도는 알아둘 가치가 있다.
* **XREADGROUP**은 스트림으로부터 데이터를 읽는 것암에도 *write command*로 분류된다. 데이터의 읽기의 부수적인 효과로 컨슈머 그룹이 변경되기 때문에, 오직 마스터 노드에서만 호출된다.

다음은 컨슈머 그룹을 사용한 컨슈머 구현의 예로, 루비로 작성되었다. 이 루비 코드는 다른 언어로 프로그래밍을 하고, 루비는 잘 모르는 거의 모든 숙련된 프로그래머가 읽을 수 있는 방식으로 작성되었다:

```ruby
require 'redis'

if ARGV.length == 0
    puts "Please specify a consumer name"
    exit 1
end

ConsumerName = ARGV[0]
GroupName = "mygroup"
r = Redis.new

def process_message(id,msg)
    puts "[#{ConsumerName}] #{id} = #{msg.inspect}"
end

$lastid = '0-0'

puts "Consumer #{ConsumerName} starting..."
check_backlog = true
while true
    # Pick the ID based on the iteration: the first time we want to
    # read our pending messages, in case we crashed and are recovering.
    # Once we consumed our history, we can start getting new messages.
    if check_backlog
        myid = $lastid
    else
        myid = '>'
    end

    items = r.xreadgroup('GROUP',GroupName,ConsumerName,'BLOCK','2000','COUNT','10','STREAMS',:my_stream_key,myid)

    if items == nil
        puts "Timeout!"
        next
    end

    # If we receive an empty reply, it means we were consuming our history
    # and that the history is now empty. Let's start to consume new messages.
    check_backlog = false if items[0][1].length == 0

    items[0][1].each{|i|
        id,fields = i

        # Process the message
        process_message(id,fields)

        # Acknowledge the message as processed
        r.xack(:my_stream_key,GroupName,id)

        $lastid = id
    }
end
```

여기서 볼 수 있듯이, 이 아이디어는 히스토리를 소비하는 것으로 시작하고, 그 히스토리는 보류중인 메시지의 리스트이다. 전에 컨슈머가 크래시되어 재시작이 된다면, 우리는 전송은 되었지만 아직 응답(ACK)를 받지 못한 메시지를 다시 읽어야 할 때, 이것은 유용하다. 이 방식으로 우리는 메시지를 여러번 처리하거나 한 번만 처리할 수 있다. (적어도 컨슈머의 실패의 경우, 하지만 레디스의 영속성과 리플리케이션을 포함하는 제한 사항 또한 있다. 이 주제에 대해서는 이후의 섹션을 참고하라.)

한 번 히스토리가 소비되고, 비어있는 메시지 리스트를 받게 되면, 새로운 메시지를 소비하기 위해 `>` 특별 ID로 변경할 수 있다.

## Recovering from permanent failures

위의 예는 메시지의 서브셋 각각을 얻고, 클라이언트로 전달되었지만 아직 보류중인 메시지를 다시 읽어 실패 상태를 복구하는, 동일한 컨슈머 그룹에 참가하는 컨슈머를 작성하도록 해준다. 하지만 현실에서는 컨슈머는 영구적으로 실패하고 절대 복구될 수 없을지도 모른다. 어떠한 이유때문에 멈춘 이후 복구되지 못하는 컨슈머의 보류중인 메시지에는 무슨 일이 발생할까?

레디스 컨슈머 그룹은 이러한 상황에서 주어진 컨슈머의 보류중인 메시지를 클레임(*claim*)하기 위해서 사용할 수 있는 기능으로, 그러한 메시지의 소유권을 변경하고, 다른 컨슈머로 다시 할당한다. 이 기능은 매우 명시적인데, 컨슈머는 보류중인 메시지의 목록을 검사하고, 지정한 메시지를 특별한 커맨드를 이용해서 클레임(claim)해야 하는데, 그렇지 않으면 서버는 영원히 보류중인 메시지를 오래된 컨슈머로 할당해둔다. 이러한 방법으로 각각의 어플리케이션은 이러한 기능을 이용할지 말지, 그리고 정확하게 그 기능을 사용할지를 선택할 수 있다.

이 프로세스의 첫 번째 단계는 단순히 **XPENDING** 커맨드를 이용하는 것이고, 이것은 컨슈머 내의 보류 상태를 관찰할 수 있게 한다. 이것은 read-only 커맨드로, 호출로부터 안전하며 어떤 메시지의 소유권도 변경하지 않는다. 단순한 양식으로, 이 커맨드는 스트림의 이름과 컨슈머 그룹의 이름, 두개의 인수와 함께 호출된다.


```
> XPENDING mystream mygroup
1) (integer) 2
2) 1526569498055-0
3) 1526569506935-0
4) 1) 1) "Bob"
      2) "2"
```

이러한 방식으로 호출될 때, 커맨드는 그룹 내에서 보류중인 메시지의 총 개수를 표시하며, 이번 경우에는 2개의 메시지가 표시된다. 보류중인 메시지의 ID가 제일 작은 것과 큰 것이 표기되며, 마지막으로는 보류중인 메시지를 가진 컨슈머의 리스트와 각각 보유한 보류중의 메시지의 개수를 출력한다. 여기서는 2개의 보류중인 Bob이 표기되는데, Alice가 요청한 메시지에 대해서만 **XACK**를 이용해서 응답이 있었기 때문이다.

**XPENDING**에 더 많은 인수를 주어 더 많은 정보를 요청할 수도 있는데, 전체 커맨드 시그내쳐는 다음과 같기 때문이다.

```
XPENDING <key> <groupname> [<start-id> <end-id> <count> [<consumer-name>]]
```

*시작(start-id) ID*와  *끝 ID(end-id)* (단순히 **XRANGE**와 같이 `-`와 `+`를 부여할 수도 있다.)와 커맨드에 의해 반환될 정보의 전체 수를 제어할 *개수(count-id)* 를 부여함으로써, 우리는 보류중인 메시지에 대해 더 많은 것을 알 수 있다. 선택적인 인수중 마지막인 *컨슈머명(consumer-name)* 은 주어진 컨슈머에 대해서만 보류중인 메시지를 출력하도록 제한하고자 할 때 사용되지만, 다음 예에서 이 기능은 사용하지 않을 것이다. 

```
> XPENDING mystream mygroup - + 10
1) 1) 1526569498055-0
   2) "Bob"
   3) (integer) 74170458
   4) (integer) 1
2) 1) 1526569506935-0
   2) "Bob"
   3) (integer) 74170458
   4) (integer) 1
```

이제 각 메시지에 대한 상세 정보를 확인할 수 있는데, *ID* 와 *컨슈머명*, 컨슈머로 메시지가 전달된 이후, 얼마나 많은 밀리초동안의 시간이 지났는가를 확인할 수 있는 *유휴 시간* , 그리고 마지막으로 *메시지가 전달된 시간* 을 알 수 있다. Bob으로부터 2개의 메시지가 있고, 74170458 밀리초 동안 유효 상태였으며, 이것은 대략 20시간이다.

**XRANGE**만을 이용해서 첫 메시지의 내용이 무엇인지 확인할 수 있는 사람이 아무도 없음을 유의하라.


```
> XRANGE mystream 1526569498055-0 1526569498055-0
1) 1) 1526569498055-0
   2) 1) "message"
      2) "orange"
```

단순히 동일한 ID를 인수로 2번 반복해서 사용해야한다. 이제 우리는 이렇게 생각해볼 수 있는데, Alice는 메시지가 처리되지 않은 20시간 후에도 Bob이 시간내에 복구되지 않을 것이라고 판단할 수 있으며, 그러한 메시지에 대해서는 *claim* 하고, Bob을 대신해서 처리를 재개할 것이다. 그렇게 하기 위해, **XCLAIM** 커맨드를 사용한다.

이 커맨드는 매우 복잡하고, 전체 형식의 옵션으로 가득한데, 컨슈머 그룹의 변경의 복제를 위해 사용되기 때문이다. 하지만 우리는 일반적으로 필요한 인수만을 사용한다. 이러한 경우에 다음과 같이 호출하는 것만큼 간단하다.

```
XCLAIM <key> <group> <consumer> <min-idle-time> <ID-1> <ID-2> ... <ID-N>
```

이 명령으로, 지정한 키와 그룹에 대해 명시된 ID들의 소유권을 변경할 것이고, `<consumer>`에 지정된 컨슈머명으로 할당될 것이라고 말해준다. 그러나 또, 최소한의 유휴 시간을 지정하면, 언급된 메시지의 유휴 시간이 이 커맨드에서 지정한 유휴 시간보다 큰 것에 대해서만 동작하게 된다. 이것은 두 개의 클라이언트가 동시에 메시지를 차지하려고 시도할지도 모르기 때문에 유용하다:

```
Client 1: XCLAIM mystream mygroup Alice 3600000 1526569498055-0
Client 2: XCLAIM mystream mygroup Lora 3600000 1526569498055-0
```

그러나 메시지를 차지(claim)하려고 하는 것의 사이드 이펙트로 메시지의 유휴 시간을 초기화시키는 것이 있다! 그리고 전달된 메시지의 카운트를 증가시킨다. 그래서 두 번째 클라이언트는 클레임에 실패할 것이다. 이러한 방법으로 우리는 메시지의 사소한 재처리를 피할 수 있다. (심지어 일반적으로 정확히 한 번만 처리할 수 없는 경우에도)

이것은 명령의 실행 결과이다:

```
> XCLAIM mystream mygroup Alice 3600000 1526569498055-0
1) 1) 1526569498055-0
   2) 1) "message"
      2) "orange"
```

이 메시지는 Alice에 의해 성공적으로 클레임이 되었고, 그래서 이제 메시지를 처리하고, 메시지를 받았음을 알릴 수 있다(ACK). 그리고 심지어 원래 컨슈머가 복구되지 않고 있더라도 상황을 진전시킬 수 있다.

위의 예로에서 보듯이, 주어진 메시지를 성공적으로 클레임하는 것의 사이드 이펙트로써, **XCLAIM** 커맨드는 또한 메시지를 반환하는 것은 명백하다. 그러나 이것은 필수가 아니다. 성공적으로 클레임된 메시지의 ID만을 리턴하기 위해서 **JUSTID** 옵션이 사용될 수 있다. 서버와 클라이언트간에 사용되는 네트워크 대역폭을 줄이기를 원하거나, 때때로 보류중인 메시지를 다시 스캔하는 방식으로 컨슈머가 구현되어 메시지를 읽을 필요가 없는 경우에는 이 옵션이 유용하다.

클레임하는 것은 단계를 나누어 구현될 수도 있다: 첫 째, 보류중인 메시지의 목록을 체크하고, 유휴 메시지를 활성 상태의 컨슈머로 할당한다. 활성 상태의 컨슈머는 레디스 스트림의 관측 기능의 하나를 사용해서 획득할 수 있다. 이것은 다음 섹션의 주제이다.

## Claiming and the delivery counter

**XPENDING** 출력 결과에서 관측할 수 있는 카운터는 각 메시지의 전송 수이다. 그러한 카운터는 두 가지 방식으로 증가된다: **XCLAIM**에 의해 메시지가 성공적으로 클레임되었을 때, 또는 보류 메시지의 히스토리에 접근하기 위해 **XREADGROUP**이 호출이 사용되는 경우이다.

실패가 있을 때, 메시지가 여러 번 전달되는 것이 일반적이지만, 결국 그 메시지들은 처리되는 것이 보통이다. 하지만 메시지 처리 코드에 버그가 발생하는 식으로 손상되거나 조작되기 때문에, 메시지를 처리하는 데에 문제가 있는 경우가 있다. 그러한 경우 컨슈머는 지속적으로 특정 메시지의 처리에 실패하는 일이 발생할 것이다. 때문에 우리는 전송을 시도에 대한 카운터를 가지고 있고, 어떠한 이유로 전혀 처리가 가능하지 않은 메시지를 발견하는데 이를 사용할 수 있다. 그래서 전송 카운터가 당신이 생각하는 큰 수에 도달하면, 그러한 메시지를 다른 스트림에 넣고, 시스템 관리자에게 알리는 편이 아마 현명할 것이다. 이것은 레디스 스트림이 *dead letter* 라는 컨셉을 구현하는 기본적인 방식이다.

## Streams observability

관측이 부족한 메시징 시스템은 작업하기가 매우 어렵다. 어떤 것이 메시지를 소비하고 있는지, 무슨 메시지가 보류 중인지, 주어진 스트림 내의 컨슈머 그룹의 집합을 알지 못한다면 모든 것이 불투명해진다. 이러한 이유로, 레디스 스트림과 컨슈머 그룹은 무엇이 일어났는지 관측하기 위해서 각각의 방법을 가진다. 이미 다룬 **XPENDING**은 유휴 시간과 전송 회수와 함께 주어진 순간에 처리중인 메시지의 리스트를 검사하게 해준다.

그러나 우리는 그보다 더 많은 것들을 조사할 수 있기를 원할지도 모르며, **XINFO** 커맨드는 스트림이나 컨슈머 그룹에 대한 정보를 얻기 위해 서브 커맨드와 함께 사용될 수 있는 관측가능한  인터페이스이다.

이 커맨드는 스트림과 컨슈머의 상태에 대해 각각 다른 정보를 보여주기 위해 서브 커맨드를 사용한다. 예를 들어, **XINFO STREAM <key>** 는 스트림 자체에 대한 정보를 보고한다.

```
> XINFO STREAM mystream
 1) length
 2) (integer) 13
 3) radix-tree-keys
 4) (integer) 1
 5) radix-tree-nodes
 6) (integer) 2
 7) groups
 8) (integer) 2
 9) first-entry
10) 1) 1526569495631-0
    2) 1) "message"
       2) "apple"
11) last-entry
12) 1) 1526569544280-0
    2) 1) "message"
       2) "banana"
```

이 출력 결과는 어떻게 스트림이 내부적으로 인코딩되었는지에 대한 정보를 보여주고, 또한 스트림내의 첫 번째와 마지막 메시지를 보여준다. 사용할 수 있는 또 다른 정보는 이 스트림의 값과 관련된 컨슈머 그룹의 수이다. 우리는 컨슈머 그룹에 대한 더 많은 정보를 요청함으로써 더 파헤칠 수 있다.

```
> XINFO GROUPS mystream
1) 1) name
   2) "mygroup"
   3) consumers
   4) (integer) 2
   5) pending
   6) (integer) 2
2) 1) name
   2) "some-other-group"
   3) consumers
   4) (integer) 1
   5) pending
   6) (integer) 0
```

이번과 지난 출력 결과에서 볼 수 있듯이, **XINFO** 커맨드는 일련의 필드-값 아이템을 출력한다. 관측 가능한 커맨드이기 때문에, 이것은 무슨 정보가 보고되는지 사람이 즉시 이해할 수 있도록 해주고,  오래된 클라이언트와의 호환성을 헤치지 않고 더 많은 필드를 추가함으로써 미래에는 더 많은 정보를 보고할 수 있도록 해준다. 이외의 커맨드들은 대신 더 효율적으로 대역폭을 사용해야하는 이외의 커맨드들은 단지 필드명 없는 정보만을 보고하면 된다.

**GROUPS** 서브 커맨드가 사용된 위 예의 출력 결과에서 필드명을 명확히 관찰해야 한다. 해당 컨슈머 그룹에 등록된 컨슈머를 체크함으로써 지정한 컨슈머 그룹의 상태의 더욱 상세하게 체크할 수 있다.

```
> XINFO CONSUMERS mystream mygroup
1) 1) name
   2) "Alice"
   3) pending
   4) (integer) 1
   5) idle
   6) (integer) 9104628
2) 1) name
   2) "Bob"
   3) pending
   4) (integer) 1
   5) idle
   6) (integer) 83841983
```

이러한 경우 커맨드의 문법을 기억하지 못한다면, 커맨드 자신에 도움을 요청하라:

```
> XINFO HELP
1) XINFO <subcommand> arg arg ... arg. Subcommands are:
2) CONSUMERS <key> <groupname>  -- Show consumer groups of group <groupname>.
3) GROUPS <key>                 -- Show the stream consumer groups.
4) STREAM <key>                 -- Show information about the stream.
5) HELP                         -- Print this help.
```

## Differences with Kafka (TM) partitions

레디스 스트림의 컨슈머 그룹은 어떠한 형태로 Kafka (TM)의 파티셔닝 기반의 컨슈머 그룹과 닮았을지도 모른다. 하지만 레디스 스트림은 실질적으로 매우 다르다는 것을 참고하라. 파티션은 오직 *논리적(logical)* 이고, 메시지는 단지 하나의 레디스 키에 입력되며, 각각 다른 클라이언트로 제공되는 방법은 어떠한 컨슈머가 새로운 메시지를 처리할 준비가 되었는지에 기반하지, 어떤 파티션 클라이언트가 읽고 있는지는 아니다. 예를 들어, 컨슈머 C3이 어느 시점에 영구적으로 실패하면, 레디스는 이제 2개의 *논리적(logical)*인 파티션만 있는 것처럼, C1과 C2로 도착하는 모든 메시지를 계속해서 전달할 것이다.

마찬가지로, 주어진 컨슈머가 메시지를 처리하는데에 있어 다른 컨슈머보다 훨씬 빠르다면, 이 컨슈머는 동일한 시간 단위 내에서 비례적으로 더 많은 메시지를 받을 것이다. 이것은 레디스가 명시적으로 수신 통지를 받지 못한 모든 메시지를 추적하고, 어떤 컨슈머가 어떤 메시지를 받았는지와 어떤 컨슈머로도 전달된 적이 없는 첫 번째 메시지의 ID를 기억하기 때문이 가능하다.

그러나, 이것은 또한 의미한다. 레디스에서 동일한 스트림의 메시지를 여러 레디스 인스턴스로 파티션하기를 원한다면, 여러 개의 키와, 레디스 클러스터(Redis Cluster)나 어플리케이션 특정(application-specific) 샤딩과 같은 샤딩 시스템을 이용해야 한다. 단일 레디스 스트림은 여러 인스턴스로 자동으로 파티션되지 않는다.

도식적으로 다음과 같은 것이 사실이라고 말할 수 있다.

* 스트림 하나와 컨슈머 하나를 사용한다면, 메시지를 순서대로 처리할 것이다.
* N개의 스트림을 N개의 컨슈머와 함께 사용한다면, 그래서 오직 하나의 컨슈머만 N개의 스트림의 서브셋에 히트하도록 하면, 위의 `1 stream -> 1 consumer` 모델을 확장할 수 있다.
* 하나의 스트림을 N개의 컨슈머로 처리하면, N개의 컨슈머로 로드 밸런싱할 수 있다. 하지만 이러한 경우, 동일한 논리적인 아이템에 대한 메시지는 순서와 상관없이 소비될 것이다. 주어진 컨슈머는 메시지 3를 다른 컨슈머가 처리중인 메시지 4보다 빠르게 처리할지도 모른다.

그래서 기본적으로 카프카 파티션은 N개의 레디스 키를 이용하는 것과 좀 더 비슷하다. 반면에, 레디스 컨슈머 그룹은 메시지를 주어진 스트림 하나로부터 N개의 각각의 컨슈머들로 보내는, 메시지의 서버사이드 로드밸런싱 시스템이다.

## Capped Streams

많은 어플리케이션은 스트림으로 데이터를 영원히 수집하기를 원하지 않을 것이다. 때때로 스트림내의 최대 아이템 개수를 가지는 것이 유용하며, 다른 시점에 최대 사이즈에 도달한다면, 데이터를 레디스로부터 메모리가 아니라 그 만큼 빠르지는 않지만, 잠재적으로 십여년이 될 수도 있는 히스토리를 저장하는데 적합한 스토리지로 옮기는 것이 유용하다. 레디스 스트림은 이를 위한 몇 가지를 지원한다. 하나는 **XADD** 커맨드의**MAXLEN** 옵션이다. 이 옵션을 사용하는 것은 매우 단순한다:

```
> XADD mystream MAXLEN 2 * value 1
1526654998691-0
> XADD mystream MAXLEN 2 * value 2
1526654999635-0
> XADD mystream MAXLEN 2 * value 3
1526655000369-0
> XLEN mystream
(integer) 2
> XRANGE mystream - +
1) 1) 1526654999635-0
   2) 1) "value"
      2) "2"
2) 1) 1526655000369-0
   2) 1) "value"
      2) "3"
```

**MAXLEN**을 사용하면, 지정된 길이에 도달될 때, 오래된 엔트리는 자동으로 제거된다. 따라서 스트림은 일정한 사이즈를 유지한다. 현재는 스트림이 지정된 것보다 더 오래되지 않은 아이템만을  유지하게 하는 옵션이 없기 때문에, 일관성있게 실행되기 위한 이러한 커맨드는 아이템을 제거하기 위해서 많은 시간동안 블로킹을 해야한다. 예를 들어, 입력에 대한 스파이크가 있어, 오랜 시간 동안 멈추고, 또 다른 입력 모두 동일한 최대 시간이 걸린다면 무슨 일이 일어날지 상상해보자. 스트림은  멈춰있는 동안 너무 오래되어 버린 데이터를 제거하기 위해 블록할 것이다. 그래서 이것은 유저가 어떤 계획을 실행하고, 이상적인 스트림의 최대 길이가 무엇인지 이해하는 것에 달려있다. 게다가, 스트림의 길이는 메모리의 사용에 비례하기 때문에, 시간에 의한 트림은 제어와 예측이 덜 간단하다: 입력 비율에 달려있다. 그 비율은 종종 시간에 따라 변하는 변수이다 (그리고 변경이 없다면, 사이즈에 따라 트림하는 것은 간단한 일이다).

그러나 **MAXLEN**으로 트림을 하는 것은 비용이 크다: 스트림은 매우 메모리를 효율적으로 사용하기 위해 매크로(macro) 노드에서 radix 트리로 표현한다. 수십개의 엘리먼트로 구성되는 단일 매크로 노드를 변경하는 것은 최적이 아니다. 그래서 다음과 같이 특별한 형태로 커맨드를 실행하는 것이 가능하다:

```
XADD mystream MAXLEN ~ 1000 * ... entry fields here ...
```

The `~` argument between the **MAXLEN** option and the actual count means, I don't really need this to be exactly 1000 items. It can be 1000 or 1010 or 1030, just make sure to save at least 1000 items. With this argument, the trimming is performed only when we can remove a whole node. This makes it much more efficient, and it is usually what you want.

There is also the **XTRIM** command available, which performs something very similar to what the **MAXLEN** option does above, but this command does not need to add anything, it can be run against any stream in a standalone way.

```
> XTRIM mystream MAXLEN 10
```

Or, as for the **XADD** option:

```
> XTRIM mystream MAXLEN ~ 10
```

However, **XTRIM** is designed to accept different trimming strategies, even if currently only **MAXLEN** is implemented. Given that this is an explicit command, it is possible that in the future it will allow to specify trimming by time, because the user calling this command in a stand-alone way is supposed to know what she or he is doing.

One useful eviction strategy that **XTRIM** should have is probably the ability to remove by a range of IDs. This is currently not possible, but will be likely implemented in the future in order to more easily use **XRANGE** and **XTRIM** together to move data from Redis to other storage systems if needed.

## Special IDs in the streams API

You may have noticed that there are several special IDs that can be
used in the Redis streams API. Here is a short recap, so that they can make more
sense in the future.

The first two special IDs are `-` and `+`, and are used in range queries with the `XRANGE` command. Those two IDs respectively mean the smallest ID possible (that is basically `0-1`) and the greatest ID possible (that is `18446744073709551615-18446744073709551615`). As you can see it is a lot cleaner to write `-` and `+` instead of those numbers.

Then there are APIs where we want to say, the ID of the item with the greatest ID inside the stream. This is what `$` means. So for instance if I want only new entries with `XREADGROUP` I use such ID to tell that I already have all the existing entries, but not the new ones that will be inserted in the future. Similarly when I create or set the ID of a consumer group, I can set the last delivered item to `$` in order to just deliver new entries to the consumers using the group.

As you can see `$` does not mean `+`, they are two different things, as `+` is the greatest ID possible in every possible stream, while `$` is the greatest ID in a given stream containing given entries. Moreover APIs will usually only understand `+` or `$`, yet it was useful to avoid loading a given symbol with multiple meanings.

Another special ID is `>`, that is a special meaning only related to consumer groups and only when the `XREADGROUP` command is used. Such special ID means that we want only entries that were never delivered to other consumers so far. So basically the `>` ID is the *last delivered ID* of a consumer group.

Finally the special ID `*`, that can be used only with the `XADD` command, means to auto select an ID for us for the new entry.

So we have `-`, `+`, `$`, `>` and `*`, and all have a different meaning, and most of the times, can be used in different contexts.

## Persistence, replication and message safety

A Stream, like any other Redis data structure, is asynchronously replicated to slaves and persisted into AOF and RDB files. However what may not be so obvious is that also consumer groups full state is propagated to AOF, RDB and slaves, so if a message is pending in the master, also the slave will have the same information. Similarly, after a restart, the AOF will restore the consumer groups state.

However note that Redis streams and consumer groups are persisted and replicated using the Redis default replication, so:

* AOF must be used with a strong fsync policy if persistence of messages is important in your application.
* By default the asynchronous replication will not guarantee that **XADD** commands or consumer groups state changes are replicated: after a failover something can be missing depending on the ability of slaves to receive the data from the master.
* The **WAIT** command may be used in order to force the propagation of the changes to a set of slaves. However note that while this makes it very unlikely that data is lost, the Redis failover process as operated by Sentinel or Redis Cluster performs only a *best effort* check to failover to the slave which is the most updated, and under certain specific failures may promote a slave that lacks some data.

So when designing an application using Redis streams and consumer groups, make sure to understand the semantical properties your application should have during failures, and configure things accordingly, evaluating if it is safe enough for your use case.

## Removing single items from a stream

Streams also have a special command to remove items from the middle of a stream, just by ID. Normally for an append only data structure this may look like an odd feature, but it is actually useful for applications involving, for instance, privacy regulations. The command is called **XDEL**, and will just get the name of the stream followed by the IDs to delete:

```
> XRANGE mystream - + COUNT 2
1) 1) 1526654999635-0
   2) 1) "value"
      2) "2"
2) 1) 1526655000369-0
   2) 1) "value"
      2) "3"
> XDEL mystream 1526654999635-0
(integer) 1
> XRANGE mystream - + COUNT 2
1) 1) 1526655000369-0
   2) 1) "value"
      2) "3"
```

However in the current implementation, memory is not really reclaimed until a macro node is completely empty, so you should not abuse this feature.

## Zero length streams

A difference between streams and other Redis data structures is that when the other data structures have no longer elements, as a side effect of calling commands that remove elements, the key itself will be removed. So for instance, a sorted set will be completely removed when a call to **ZREM** will remove the last element in the sorted set. Streams instead are allowed to stay at zero elements, both as a result of using a **MAXLEN** option with a count of zero (**XADD** and **XTRIM** commands), or because **XDEL** was called.

The reason why such an asymmetry exists is because Streams may have associated consumer groups, and we do not want to lose the state that the consumer groups define just because there are no longer items inside the stream. Currently the stream is not deleted even when it has no associated consumer groups, but this may change in the future.

## Total latency of consuming a message

Non blocking stream commands like XRANGE and XREAD or XREADGROUP without the BLOCK option are served synchronously like any other Redis command, so to discuss latency of such commands is meaningless: it is more interesting to check the time complexity of the commands in the Redis documentation. It should be enough to say that stream commands are at least as fast as sorted set commands when extracting ranges, and that `XADD` is very fast and can easily insert from half million to one million of items per second in an average machine if pipelining is used.

However latency becomes an interesting parameter if we want to understand the delay of processing the message, in the context of blocking consumers in a consumer group, from the moment the message is produced via `XADD`, to the moment the message is obtained by the consumer because `XREADGROUP` returned with the message.

## How serving blocked consumers work

Before providing the results of performed tests, it is interesting to understand what model Redis uses in order to route stream messages (and in general actually how any blocking operation waiting for data is managed).

* The blocked client is referenced in an hash table that maps keys for which there is at least one blocking consumer, to a list of consumers that are waiting for such key. This way, given a key that received data, we can resolve all the clients that are waiting for such data.
* When a write happens, in this case when the `XADD` command is called, it calls the `signalKeyAsReady()` function. This function will put the key into a list of keys that need to be processed, because such keys may have new data for consumers blocked. Note that such *ready keys* will be processed later, so in the course of the same event loop cycle, it is possible that the key will receive other writes.
* Finally, before returning into the event loop, the *ready keys* are finally processed. For each key the list of clients waiting for data is ran, and if applicable, such clients will receive the new data that arrived. In the case of streams the data is the messages in the applicable range requested by the consumer.

As you can see, basically, before returning to the event loop both the client calling `XADD` that the clients blocked to consume messages, will have their reply in the output buffers, so the caller of `XADD` should receive the reply from Redis about at the same time the consumers will receive the new messages.

This model is *push based*, since adding data to the consumers buffers will be performed directly by the action of calling `XADD`, so the latency tends to be quite predictable.

## Latency tests results

In order to check this latency characteristics a test was performed using multiple instances of Ruby programs pushing messages having as an additional field the computer millisecond time, and Ruby programs reading the messages from the consumer group and processing them. The message processing step consisted in comparing the current computer time with the message timestamp, in order to understand the total latency.

Such programs were not optimized and were executed in a small two core instance also running Redis, in order to try to provide the latency figures you could expect in non optimal conditions. Messages were produced at a rate of 10k per second, with ten simultaneous consumers consuming and acknowledging the messages from the same Redis stream and consumer group.


Results obtained:

```
Processed between 0 and 1 ms -> 74.11%
Processed between 1 and 2 ms -> 25.80%
Processed between 2 and 3 ms -> 0.06%
Processed between 3 and 4 ms -> 0.01%
Processed between 4 and 5 ms -> 0.02%
```

So 99.9% of requests have a latency <= 2 milliseconds, with the outliers that remain still very close to the average.

Adding a few million unacknowledged messages to the stream does not change the gist of the benchmark, with most queries still processed with very short latency.

A few remarks:

* Here we processed up to 10k messages per iteration, this means that the `COUNT` parameter of XREADGROUP was set to 10000. This adds a lot of latency but is needed in order to allow the slow consumers to be able to keep with the message flow. So you can expect a real world latency that is a lot smaller.
* The system used for this benchmark is very slow compared to today's standards.