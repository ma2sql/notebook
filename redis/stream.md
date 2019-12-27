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

Assuming I have a key `mystream` of type stream already existing, in order to create a consumer group I need to do just the following:

```
> XGROUP CREATE mystream mygroup $
OK
```

As you can see in the command above when creating the consumer group we have to specify an ID, which in the example is just `$`. This is needed because the consumer group, among the other states, must have an idea about what message to serve next at the first consumer connecting, that is, what is the current *last message ID* when the group was just created? If we provide `$` as we did, then only new messages arriving in the stream from now on will be provided to the consumers in the group. If we specify `0` instead the consumer group will consume *all* the messages in the stream history to start with. Of course, you can specify any other valid ID. What you know is that the consumer group will start delivering messages that are greater than the ID you specify. Because `$` means the current greatest ID in the stream, specifying `$` will have the effect of consuming only new messages.

`XGROUP CREATE` also supports creating the stream automatically, if it doesn't exist, using the optional `MKSTREAM` subcommand as the last argument:

```
> XGROUP CREATE newstream mygroup $ MKSTREAM
OK
```

Now that the consumer group is created we can immediately start trying to read messages via the consumer group, by using the **XREADGROUP** command. We'll read from the consumers, that we will call Alice and Bob, to see how the system will return different messages to Alice and Bob.

**XREADGROUP** is very similar to **XREAD** and provides the same **BLOCK** option, otherwise it is a synchronous command. However there is a *mandatory* option that must be always specified, which is **GROUP** and has two arguments: the name of the consumer group, and the name of the consumer that is attempting to read. The option **COUNT** is also supported and is identical to the one in **XREAD**.

Before reading from the stream, let's put some messages inside:

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

Note: *here message is the field name, and the fruit is the associated value, remember that stream items are small dictionaries.*

It is time to try reading something using the consumer group:

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
