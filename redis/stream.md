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

Note that in the example above, other than removing **COUNT**, I specified the new **BLOCK** option with a timeout of 0 milliseconds (that means to never timeout). Moreover, instead of passing a normal ID for the stream `mystream` I passed the special ID `$`. This special ID means that **XREAD** should use as last ID the maximum ID already stored in the stream `mystream`, so that we will receive only *new* messages, starting from the time we started listening. This is similar to the `tail -f` Unix command in some way.

Note that when the **BLOCK** option is used, we do not have to use the special ID `$`. We can use any valid ID. If the command is able to serve our request immediately without blocking, it will do so, otherwise it will block. Normally if we want to consume the stream starting from new entries, we start with the ID `$`, and after that we continue using the ID of the last message received to make the next call, and so forth.

The blocking form of **XREAD** is also able to listen to multiple Streams, just by specifying multiple key names. If the request can be served synchronously because there is at least one stream with elements greater than the corresponding ID we specified, it returns with the results. Otherwise, the command will block and will return the items of the first stream getting new data (according to the specified ID).

Similarly to blocking list operations, blocking stream reads are *fair* from the point of view of clients waiting for data, since the semantics is FIFO style. The first client that blocked for a given stream is the first that will be unblocked as new items are available.

**XREAD** has no other options than **COUNT** and **BLOCK**, so it's a pretty basic command with a specific purpose to attach consumers to one or multiple streams. More powerful features to consume streams are available using the consumer groups API, however reading via consumer groups is implemented by a different command called **XREADGROUP**, covered in the next section of this guide.

## Consumer groups
