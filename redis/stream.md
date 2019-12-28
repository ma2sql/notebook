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

**XREADGROUP** replies are just like **XREAD** replies. Note however the `GROUP <group-name> <consumer-name>` provided above, it states that I want to read from the stream using the consumer group `mygroup` and I'm the consumer `Alice`. Every time a consumer performs an operation with a consumer group, it must specify its name uniquely identifying this consumer inside the group.

There is another very important detail in the command line above, after the mandatory **STREAMS** option the ID requested for the key `mystream` is the special ID `>`. This special ID is only valid in the context of consumer groups, and it means: **messages never delivered to other consumers so far**.

This is almost always what you want, however it is also possible to specify a real ID, such as `0` or any other valid ID, in this case however what happens is that we request to **XREADGROUP** to just provide us with the **history of pending messages**, and in such case, will never see new messages in the group. So basically **XREADGROUP** has the following behavior based on the ID we specify:

* If the ID is the special ID `>` then the command will return only new messages never delivered to other consumers so far, and as a side effect, will update the consumer group *last ID*.
* If the ID is any other valid numerical ID, then the command will let us access our *history of pending messages*. That is, the set of messages that were delivered to this specified consumer (identified by the provided name), and never acknowledged so far with **XACK**.

We can test this behavior immediately specifying an ID of 0, without any **COUNT** option: we'll just see the only pending message, that is, the one about apples:

```
> XREADGROUP GROUP mygroup Alice STREAMS mystream 0
1) 1) "mystream"
   2) 1) 1) 1526569495631-0
         2) 1) "message"
            2) "apple"
```

However, if we acknowledge the message as processed, it will no longer be part of the pending messages history, so the system will no longer report anything:

```
> XACK mystream mygroup 1526569495631-0
(integer) 1
> XREADGROUP GROUP mygroup Alice STREAMS mystream 0
1) 1) "mystream"
   2) (empty list or set)
```

Don't worry if you yet don't know how **XACK** works, the concept is just that processed messages are no longer part of the history that we can access.

Now it's the turn of Bob to read something:

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

Bob asked for a maximum of two messages and is reading via the same group `mygroup`. So what happens is that Redis reports just *new* messages. As you can see the "apple" message is not delivered, since it was already delivered to Alice, so Bob gets orange and strawberry, and so forth.

This way Alice, Bob, and any other consumer in the group, are able to read different messages from the same stream, to read their history of yet to process messages, or to mark messages as processed. This allows creating different topologies and semantics to consume messages from a stream.

There are a few things to keep in mind:

* Consumers are auto-created the first time they are mentioned, no need for explicit creation.
* Even with **XREADGROUP** you can read from multiple keys at the same time, however for this to work, you need to create a consumer group with the same name in every stream. This is not a common need, but it is worth to mention that the feature is technically available.
* **XREADGROUP** is a *write command* because even if it reads from the stream, the consumer group is modified as a side effect of reading, so it can be only called in master instances.

An example of consumer implementation, using consumer groups, written in the Ruby language could be the following. The Ruby code is written in a way to be readable from virtually any experienced programmer programming in some other language and not knowing Ruby:

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

As you can see the idea here is to start consuming the history, that is, our list of pending messages. This is useful because the consumer may have crashed before, so in the event of a restart we want to read again messages that were delivered to us without getting acknowledged. This way we can process a message multiple times or one time (at least in the case of consumers failures, but there are also the limits of Redis persistence and replication involved, see the specific section about this topic).

Once the history was consumed, and we get an empty list of messages, we can switch to use the `>` special ID in order to consume new messages.

## Recovering from permanent failures

The example above allows us to write consumers that participate to the same consumer group, taking each a subset of messages to process, and recovering from failures re-reading the pending messages that were delivered just to them. However in the real world consumers may permanently fail and never recover. What happens to the pending messages of the consumer that never recovers after stopping for any reason?

Redis consumer groups offer a feature that is used in these situations in order to *claim* the pending messages of a given consumer so that such messages will change ownership and will be re-assigned to a different consumer. The feature is very explicit, a consumer has to inspect the list of pending messages, and will have to claim specific messages using a special command, otherwise the server will take the messages pending forever assigned to the old consumer, in this way different applications can choose if to use such a feature or not, and exactly the way to use it.

The first step of this process is just a command that provides observability of pending entries in the consumer group and is called **XPENDING**. This is just a read-only command which is always safe to call and will not change ownership of any message. In its simplest form, the command is just called with two arguments, which are the name of the stream and the name of the consumer group.

```
> XPENDING mystream mygroup
1) (integer) 2
2) 1526569498055-0
3) 1526569506935-0
4) 1) 1) "Bob"
      2) "2"
```

When called in this way the command just outputs the total number of pending messages in the consumer group, just two messages in this case, the lower and higher message ID among the pending messages, and finally a list of consumers and the number of pending messages they have. We have just Bob with two pending messages because the only message that Alice requested was acknowledged using **XACK**.

We can ask for more info by giving more arguments to **XPENDING**, because the full command signature is the following:

```
XPENDING <key> <groupname> [<start-id> <end-id> <count> [<consumer-name>]]
```

By providing a start and end ID (that can be just `-` and `+` as in **XRANGE**) and a count to control the amount of information returned by the command, we are able to know more about the pending messages. The optional final argument, the consumer name, is used if we want to limit the output to just messages pending for a given consumer, but we'll not use this feature in the following example.

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

Now we have the detail for each message: the ID, the consumer name, the *idle time* in milliseconds, which is how much milliseconds have passed since the last time the message was delivered to some consumer, and finally the number of times that a given message was delivered. We have two messages from Bob, and they are idle for 74170458 milliseconds, about 20 hours.

Note that nobody prevents us from checking what the first message content was, just using **XRANGE**.

```
> XRANGE mystream 1526569498055-0 1526569498055-0
1) 1) 1526569498055-0
   2) 1) "message"
      2) "orange"
```

We have just to repeat the same ID twice in the arguments. Now that we have some idea, Alice may decide that after 20 hours of not processing messages, Bob will probably not recover in time, and it's time to *claim* such messages and resume the processing in place of Bob. To do so, we use the **XCLAIM** command.

This command is very complex and full of options in its full form, since it is used for replication of consumer groups changes, but we'll use just the arguments that we need normally. In this case it is as simple as calling it like that:

```
XCLAIM <key> <group> <consumer> <min-idle-time> <ID-1> <ID-2> ... <ID-N>
```

Basically we say, for this specific key and group, I want that the message IDs specified will change ownership, and will be assigned to the specified consumer name `<consumer>`. However, we also provide a minimum idle time, so that the operation will only work if the idle time of the mentioned messages is greater than the specified idle time. This is useful because maybe two clients are retrying to claim a message at the same time:

```
Client 1: XCLAIM mystream mygroup Alice 3600000 1526569498055-0
Client 2: XCLAIM mystream mygroup Lora 3600000 1526569498055-0
```

However claiming a message, as a side effect will reset its idle time! And will increment its number of deliveries counter, so the second client will fail claiming it. In this way we avoid trivial re-processing of messages (even if in the general case you cannot obtain exactly once processing).

This is the result of the command execution:

```
> XCLAIM mystream mygroup Alice 3600000 1526569498055-0
1) 1) 1526569498055-0
   2) 1) "message"
      2) "orange"
```

The message was successfully claimed by Alice, that can now process the message and acknowledge it, and move things forward even if the original consumer is not recovering.

It is clear from the example above that as a side effect of successfully claiming a given message, the **XCLAIM** command also returns it. However this is not mandatory. The **JUSTID** option can be used in order to return just the IDs of the message successfully claimed. This is useful if you want to reduce the bandwidth used between the client and the server, but also the performance of the command, and you are not interested in the message because your consumer is implemented in a way that it will rescan the history of pending messages from time to time.

Claiming may also be implemented by a separate process: one that just checks the list of pending messages, and assigns idle messages to consumers that appear to be active. Active consumers can be obtained using one of the observability features of Redis streams. This is the topic of the next section.

## Claiming and the delivery counter

The counter that you observe in the **XPENDING** output is the number of deliveries of each message. Such counter is incremented in two ways: when a message is successfully claimed via **XCLAIM** or when an **XREADGROUP** call is used in order to access the history of pending messages.

When there are failures, it is normal that messages are delivered multiple times, but eventually they usually get processed. However there is sometimes a problem to process a given specific message, because it is corrupted or crafted in a way that triggers a bug in the processing code. In such a case what happens is that consumers will continuously fail to process this particular message. Because we have the counter of the delivery attempts, we can use that counter to detect messages that for some reason are not processable at all. So once the deliveries counter reaches a given large number that you chose, it is probably wiser to put such messages in another stream and send a notification to the system administrator. This is basically the way that Redis streams implement the concept of the *dead letter*.

## Streams observability

Messaging systems that lack observability are very hard to work with. Not knowing who is consuming messages, what messages are pending, the set of consumer groups active in a given stream, makes everything opaque. For this reason, Redis streams and consumer groups have different ways to observe what is happening. We already covered **XPENDING**, which allows us to inspect the list of messages that are under processing at a given moment, together with their idle time and number of deliveries.

However we may want to do more than that, and the **XINFO** command is an observability interface that can be used with sub-commands in order to get information about streams or consumer groups.

This command uses subcommands in order to show different information about the status of the stream and its consumer groups. For instance **XINFO STREAM <key>** reports information about the stream itself.

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

The output shows information about how the stream is encoded internally, and also shows the first and the last message in the stream. Another information available is the number of consumer groups associated with this stream value. We can dig further asking for more information about the consumer groups.

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

As you can see in this and in the previous output, the **XINFO** command outputs a sequence of field-value items. Because it is an observability command this allows the human user to immediately understand what information is reported, and allows the command to report more information in the future by adding more fields without breaking the compatibility with older clients. Other commands that must be more bandwidth efficient instead, like **XPENDING**, just report the information without the field names.

The output of the example above, where the **GROUPS** subcommand is used, should be clear observing the field names. We can check more in detail the state of a specific consumer group by checking the consumers that are registered in such group.

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

In case you do not remember the syntax of the command, just ask the command itself for help:

```
> XINFO HELP
1) XINFO <subcommand> arg arg ... arg. Subcommands are:
2) CONSUMERS <key> <groupname>  -- Show consumer groups of group <groupname>.
3) GROUPS <key>                 -- Show the stream consumer groups.
4) STREAM <key>                 -- Show information about the stream.
5) HELP                         -- Print this help.
```

## Differences with Kafka (TM) partitions

Consumer groups in Redis streams may resemble in some way Kafka (TM) partitioning-based consumer groups, however note that Redis streams are practically very different. The partitions are only *logical* and the messages are just put into a single Redis key, so the way the different clients are served is based on who is ready to process new messages, and not from which partition clients are reading. For instance, if the consumer C3 at some point fails permanently, Redis will continue to serve C1 and C2 all the new messages arriving, as if now there are only two *logical* partitions.

Similarly, if a given consumer is much faster at processing messages than the other consumers, this consumer will receive proportionally more messages in the same unit of time. This is possible since Redis tracks all the unacknowledged messages explicitly, and remembers who received which message and the ID of the first message never delivered to any consumer.

However, this also means that in Redis if you really want to partition messages in the same stream into multiple Redis instances, you have to use multiple keys and some sharding system such as Redis Cluster or some other application-specific sharding system. A single Redis stream is not automatically partitioned to multiple instances.

We could say that schematically the following is true:

* If you use 1 stream -> 1 consumer, you are processing messages in order.
* If you use N streams with N consumers, so that only a given consumer hits a subset of the N streams, you can scale the above model of 1 stream -> 1 consumer.
* If you use 1 stream -> N consumers, you are load balancing to N consumers, however in that case, messages about the same logical item may be consumed out of order, because a given consumer may process message 3 faster than another consumer is processing message 4.

So basically Kafka partitions are more similar to using N different Redis keys.
While Redis consumer groups are a server-side load balancing system of messages from a given stream to N different consumers.

## Capped Streams

Many applications do not want to collect data into a stream forever. Sometimes it is useful to have at maximum a given number of items inside a stream, other times once a given size is reached, it is useful to move data from Redis to a storage which is not in memory and not as fast but suited to take the history for potentially decades to come. Redis streams have some support for this. One is the **MAXLEN** option of the **XADD** command. This option is very simple to use:

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

Using **MAXLEN** the old entries are automatically evicted when the specified length is reached, so that the stream is taken at a constant size. There is currently no option to tell the stream to just retain items that are not older than a given amount, because such command, in order to run consistently, would have to potentially block for a lot of time in order to evict items. Imagine for example what happens if there is an insertion spike, then a long pause, and another insertion, all with the same maximum time. The stream would block to evict the data that became too old during the pause. So it is up to the user to do some planning and understand what is the maximum stream length desired. Moreover, while the length of the stream is proportional to the memory used, trimming by time is less simple to control and anticipate: it depends on the insertion rate that is a variable often changing over time (and when it does not change, then to just trim by size is trivial).

However trimming with **MAXLEN** can be expensive: streams are represented by macro nodes into a radix tree, in order to be very memory efficient. Altering the single macro node, consisting of a few tens of elements, is not optimal. So it is possible to give the command in the following special form:

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