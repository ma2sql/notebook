Transactions
============

`MULTI`, `EXEC`, `DISCARD` and `WATCH` are the foundation of transactions in Redis. They allow the execution of a group of commands in a single step, with two important guarantees:
Redis에서 `MULTI`, `EXEC`, `DISCARD`, 그리고 `WATCH`는 트랜잭션의 파운데이션이다. 이 명령들은 하나의 단계에서, 여러 커맨드들을 그룹으로 실행하도록 해주고, 다음의 2가지를 보장해준다.

* All the commands in a transaction are serialized and executed sequentially. It can never happen that a request issued by another client is served **in the middle** of the execution of a Redis transaction. This guarantees that the commands are executed as a single isolated operation.
* 트랜잭션 내의 모든 커맨드들은 순차적으로 직렬화되고, 실행된다. 다른 클라이언트로부터 발행된 리퀘스트는 레디스 트랜잭션이 실행되는 사이에 서빙되는 일은 결코 발생하지 않는다. 이것은 그 커맨드들이 하나의 독립된 오퍼레이션으로서 실행되는 것을 보장한다.

* Either all of the commands or none are processed, so a Redis transaction is also atomic. The `EXEC` command triggers the execution of all the commands in the transaction, so if a client loses the connection to the server in the context of a transaction before calling the `EXEC` command none of the operations are performed, instead if the `EXEC` command is called, all the operations are performed. When using the [append-only file](/topics/persistence#append-only-file) Redis makes sure to use a single write(2) syscall to write the transaction on disk However if the Redis server crashes or is killed by the system administrator in some hard way it is possible that only a partial number of operations are registered. Redis will detect this condition at restart, and will exit with an error. Using the `redis-check-aof` tool it is possible to fix the append only file that will remove the partial transaction so that the server can start again.

커맨드들은 모두 처리되거나, 아니면 하나도 처리되지 않거나 하기 때문에, 레디스 트랜잭션은 또한 원자적(atomic)이다. `EXEC` 커맨드는 트랜잭션 내의 모든 커맨드를 실행시켜서, 만약 클라이언트가 `EXEC`를 호출하기 전에 서버로의 커넥션을 잃어버렸다면 수행되는 명령은 아무것도 없으며, 반면 `EXEC`가 호출되었다면, 모든 오퍼레이션은 실행될 것이다. [append-only file](/topics/persistence#append-only-file)가 사용될 때, 레디스는 하나의 write(2) 시스템 콜을 이용해서 트랜잭션을 디스크로 쓸 수 있도록 하는데, 만약 서버가 크래시되거나 시스템 관리자에 의해 하드한 방법으로 죽었을 때, 오퍼레이션의 일부에 대해서만 등록되는 것은 발생할 수 있다. 레디스는 재시작시에 이러한 조건을 발견할 것이고, 에러와 함께 그대로 종료될 것이다. `redis-check-aof` 툴을 사용하는 것으로, AOF 파일을 수정하는 것이 가능한데, 이 때 부분 트랜잭션에 대해서는 삭제를 할 것이고, 그래서 서버는 다시 시작될 수 있을 것이다.

Starting with version 2.2, Redis allows for an extra guarantee to the above two, in the form of optimistic locking in a way very similar to a check-and-set (CAS) operation. This is documented [later](#cas) on this page.
레디스 2.2 버전부터, 레디스는 위의 두 개에 더해 추가적인 것을 보장하는데, 이는 체크와 셋(check-and-set, CAS) 오퍼레이션과 매우 유사한 방식으로 낙관적 잠금의 형식이다. 이것은 이 페이지의 뒷 부분에 기술되었다.

## Usage

A Redis transaction is entered using the `MULTI` command. The command always replies with `OK`. At this point the user can issue multiple commands. Instead of executing these commands, Redis will queue them. All the commands are executed once `EXEC` is called.
레디스 트랜잭션은 `MULTI` 커맨드를 사용해서 시작한다. 이 커맨드는 항상 `OK`를 반환한다. 유저 관점에서는 여러 커맨드를 발행할 수 있게 된다. 그러한 커맨드를 실행하지 않고, 레디스는 큐에 적재한다. 이 커맨드 모두는 `EXEC`가 호출될 때, 실행이 된다.

Calling `DISCARD` instead will flush the transaction queue and will exit the transaction.
대신 `DISCARD`를 호출하게 되면, 트랜잭션 큐는 비워지고, 트랜잭션은 종료될 것이다.

The following example increments keys `foo` and `bar` atomically.
다음의 예는 key `foo`와 `bar`를 원자적으로 증가시키는 예제이다.

    > MULTI
    OK
    > INCR foo
    QUEUED
    > INCR bar
    QUEUED
    > EXEC
    1) (integer) 1
    2) (integer) 1

As it is possible to see from the session above, `EXEC` returns an array of replies, where every element is the reply of a single command in the transaction, in the same order the commands were issued.
위의 세션으로부터 알 수 있는대로, `EXEC`는 응답(결과)의 배열을 반환하고, 모든 엘리먼트는 트랜잭션 내의 단일 커맨드의 응답이며, 발행된 커맨드의 순서와 동일하다.

When a Redis connection is in the context of a `MULTI` request, all commands will reply with the string `QUEUED` (sent as a Status Reply
from the point of view of the Redis protocol). A queued command is simply scheduled for execution when `EXEC` is called.
레디스 커넥션이 `MULTI` 요청의 문맥일 때, 모든 커맨드는 `QUEUED`라는 문자열과 함께 반환된다 (레디스 프로토콜의 관점에서는 Status Reply처럼 보내어진다.). 큐잉된 커맨드는 단순히 `EXEC`가 호출될 때, 실행되도록 스케쥴링된다.

## Errors inside a transaction

트랜잭션이 실행되는 동안, 2가지 종류의 커맨드 에러가 발생할 수 있다:

* 커맨드가 큐에 들어가는 것에 실패할 수 있어서, `EXEC`가 호출되기 전에 에러가 발생할 수 있다. 예를 들어, 커맨드가 문법적으로 잘못되거나 (인자의 수가 잘못되었거나, 커맨드명이 잘못된 경우, 등등), 또는 메모리 부족(out of memory, 서버가 `maxmemory` 지시자를 이용한 메모리 제한 등을 가지고 있다면)와 같은 심각한 조건 등이다.
* 커맨드가 `EXEC`가 호출 후에 실패할 수 있는데, 예를 들어 어느 한 키에 대해서 잘못된 값으로 오퍼레이션을 수행하는 경우(문자열 값에 대해서 리스트 오퍼레이션을 호출하는 것과 같은..)이다.

클라이언트는 큐에 들어간 커맨드의 반환값을 체크함으로써 `EXEC`가 실행되기 전에 발생하는 첫 번째 종류의 에러에 대해서는 감지할 수 있을 것이다: 만약 커맨드가 `QUEUED`와 함께 응답했다면, 올바르게 큐에 추가된 것이고, 그렇지 않으면 레디스는 에러를 반환할 것이다. 만약 큐에 들어가는 동안 에러가 있었다면, 대부분의 클라이언트는 트랜잭션을 폐기하고 중단할 것이다.

그러나 레디스 2.6.5버전부터, 서버는 커맨드를 누적시키는 동안 에러가 있었다는 것을 기억하고, 그리고 `EXEC`를 실행하는 동안에 에러를 반환하는 트랜잭션에 대한 실행을 거절할 것이고, 자동으로 트랜잭션을 폐기할 것이다.

2.6.5 버전 이전의 동작은 이전 에러와 관계없이 클라이언트가 `EXEC`를 호출한 경우에는 성공적으로 큐에 들어간 커맨드의 서브셋에 대해서만 실행하는 것이었다. 새로운 동작은 트랜잭션을 파이프라인과 혼합하는 것을 훨씬 더 간단하게 만들고, 그래서 전체 트랜잭션이 한 번에 보내질 수 있으며, 이후에 모든 응답을 한 번에 읽어낼 수가 있다.

대신 `EXEC`이후에 발생하는 에러들은 특별한 방식으로 다루어지지 않는다: 만약 일부 커맨드가 트랜잭션 동안 실패를 하더라도, 다른 모든 커맨드는 실행이 될 것이다.

이것은 프로토콜 레벨에서 좀 더 명확하다. 다음 예제에서 한 커맨드는 문법이 맞다고 하더라도 트랜잭션이 실행될 때 실패할 것이다:
                                                                                  
    Trying 127.0.0.1...
    Connected to localhost.
    Escape character is '^]'.
    MULTI
    +OK
    SET a abc
    +QUEUED
    LPOP a
    +QUEUED
    EXEC
    *2
    +OK
    -ERR Operation against a key holding the wrong kind of value

`EXEC`는 2개의 엘리먼트(two-element)를 @bulk-string-reply를 반환했고, 그 중 하나는 `OK` 코드이고, 다른 하나는 `-ERR`이다. 에러를 유저에게 제공하기 위한 합리적인 방법을 찾는 것은 클라이언트 라이브러리에 달려있다.

"**어느 한 커맨드가 실패를 하더라도, 큐 안의 다른 모든 커맨드는 처리될 것이다**"라는 것에 유의해야 한다. 레디스는 커맨드의 처리를 _멈추지 않을 것이다_.

다시 `telnet`과 함께 와이어 프로토콜을 사용하는 또 다른 예제에서는 어떻게 문법 에러를 ASAP으로 보고하는지를 보여준다:

    MULTI
    +OK
    INCR a b c
    -ERR wrong number of arguments for 'incr' command

이번에는 문법 에러 때문에 `INCR` 커맨드는 전혀 큐에 들어가지 않는다.

## Why Redis does not support roll backs?

만약 당신이 관계형 데이터베이스에 대한 배경 지식을 가지고 있다면, 레디스 커맨드가 트랜잭션동안에 실패할 수 있지만, 여전히 레디스는 롤백을 하기보다 남은 트랜잭션을 실행한다는 사실이 이상하게 보일지도 모른다.

그러나 이러한 동작에 대한 좋은 의견이 있다:

* 레디스 커맨드는 잘못된 문법으로 호출되거나 (문제는 커맨드를 큐에 들어가 있는 동안에는 발견할 수 없다), 또는 키에 대해서 잘못된 데이터 타입으로 호출되면 실패할 수 있다: 이것은 실질적인 조건에서 실패하는 커맨드는 프로그래밍 에러의 결과이고, 이러한 것은 프로덕션이 아닌 개발하는 동안 발견될 가능성이 높은 에러라는 것을 의미한다.
* 레디스는 내부적으로 단순화되어 있고 더욱 빠른데, 왜냐하면 롤백에 대한 기능이 필요하지 않기 때문이다.

레디스 관점에 대한 반론은 버그가 발생한다는 것이지만, 일반적으로는 롤백이 프로그래밍 에러로부터 당신을 지켜주니 않는다는 것에 유의해야한다. 예를 들어, 만약 쿼리가 키를 1대신에 2씩 증가시키거나, 또는 잘못된 키를 증가시킨다면, 롤백 메커니즘이 도와줄 수 있는 것은 없다. 그러한 에러로부터 그 누구도 프로그래머를 지켜줄 수가 없고, 레디스 명령이 실패하게하는 에러는 프로덕션에 입력될 가능성이 낮을 것이라는 것을 고려할 때, 에러에 대한 롤백을 지원하지 않는 더욱 심플하고 빠른 접근 방식을 선택한 것이다.


## Discarding the command queue

`DISCARD`는 트랜잭션을 취소시키기 위해서 사용될 수 있다. 이러한 경우, 실행되는 커맨드는 없고, 커넥션의 상태는 정상으로 복구된다.

    > SET foo 1
    OK
    > MULTI
    OK
    > INCR foo
    QUEUED
    > DISCARD
    OK
    > GET foo
    "1"


## Optimistic locking using check-and-set

`WATCH`는 트랜잭션에 check-and-set(CAS) 동작을 제공하기 위해 사용된다. 

`WATCH`로 감시되는 키들은 변경 사항을 발견하기 위해서 모니터링된다. 만약 `EXEC`가 실행되기전에 감시되는 키 중에서 적어도 하나에서 변경이 된다면, 전체 트랜잭션은 취소되고, `EXEC`는 트랜잭션이 실패했음을 알리기 위해서 @nil-reply를 반환한다.

예를 들어, 우리가 원자적으로 키의 값을 1씩 증가시킬 필요가 있다고 생각해보자 (레디스가 `INCR` 커맨드를 가지고 있지 않다고 가정하자).

첫 번째 시도는 아래와 같을 것이다:

    val = GET mykey
    val = val + 1
    SET mykey $val

만약 주어진 시간 내에 오퍼레이션을 수행하는 단 하나의 클라이언트만 가지고 있다면, 이것은 신뢰할 수 있게 동작할 것이다. 만약 여러 클라이언트가 키의 값을 동시에 증가시키려고 한다면, 경쟁 조건이 있을 것이다. 예를 들어, 클라이언트 A와 B는 오래된 값 10을 읽을 것이다. 두 클라이언트는 그 값을 11로 증가시킬 것이고, 최종적으로는 그 키의 값으로 `SET` 명령을 수행햐려고 할 것이다. 그래서 최종적인 값은 12가 아닌 11이 될 것이다.

Thanks to `WATCH` we are able to model the problem very well:
`WATCH` 덕분에 이러한 문제를 매우 잘 모델링할 수 있다:

    WATCH mykey
    val = GET mykey
    val = val + 1
    MULTI
    SET mykey $val
    EXEC

위의 코드를 사용해서, 만약 경쟁 조건이 있고, `WATCH`이 호출되어 `EXEC`가 호출되기까지의 시간에 또 다른 클라이언트가 `val`의 결과를 변경한다면, 트랜잭션 실패할 것이다.

우리는 단지 이번에는 새로운 경쟁 조건이 없기를 바라면서 이 작업을 반복해야한다. 이러한 잠금의 형태를 _낙관적 잠금(optimistic locking)_이라고 부르고, 이것은 매우 강력한 잠금의 형식이다. 많은 사용 예에서, 다수의 클라이언트는 서로 다른 키들에 접근할 것이고, 그래서 충돌의 가능성은 낮을 것이다. 보통의 경우에는 이러한 오퍼레이션을 반복할 필요는 없을 것이다.


## `WATCH` explained

그래서 `WATCH`는 무엇인가? 이것은 `EXEC`를 조건부로 만드는 커맨드이다: 오직 `WATCH`에 의해 감시되는 키에서 변경이 없는 경우에만 레디스에게 트랜잭션을 실행할 것을 요청하는 커맨드이다. (그러나 트랜잭션 내에서 동일한 클라이언트에 의해서 중단없이 변경될 수도 있다. [More on this](https://github.com/antirez/redis-doc/issues/734).) 그렇지 않으면 트랜잭션은 전혀 입력되지 않는다. (만약 휘발성 키를 `WATCH`로 감시하고, `WATCH`가 실행된 이후에 레디스가 그 키를 만료시킨다면, `EXEC`는 여전히 동작하는 것에 유의해야한다. [More on this](http://code.google.com/p/redis/issues/detail?id=270).)

`WATCH`는 여러 번 호출될 수 있다. 단순히 모든 `WATCH`요청은 호출이 시작되고나서부터 `EXEC`가 호출되는 순간까지, 사이에 변경을 감시하는 효과가 있다. 단일의 `WATCH` 호출에 여러 키를 보낼 수도 있다.

`EXEC`가 호출될 때, 트랜잭션이 취소되었거나 그러지 않았던지와 관계없이 모든 키는 `UNWATCH` 된다. 또한, 클라이언트 커넥션이 종료될 때 역시, 모든 것이 `UNWATCH` 된다.

또한, 모든 감시되는 키들을 비우기 위해서 (인자없이) `UNWATCH` 커맨드를 사용하는 것도 가능하다. 때때로 키를 변경하기 위해 트랜잭션을 수행하지만, 키의 현재 내용을 읽고 난 이후에는 더 이상 진행하고 싶지 않아서, 몇 개의 키를 낙관적으로 잠그려고 할 때에 이것은 유용하다. 이러한 것이 일어날 때, `UNWATCH`를 호출하기만 하면, 커넥션은 새로운 트랜잭션을 위해 자유롭게 사용될 수 있다.


### Using `WATCH` to implement ZPOP

`WATCH`가 레디스에 의해 지원되지 않는 새로운 원자적인 오퍼레이션을 만들기 위해서 사용될 수 있는 방법을 묘사하는 좋은 예제는 ZPOP(`ZPOPMIN`, `ZPOPMAX` 그리고 이것들을 블로킹하는 변형들은 5.0에서만 추가되었다.)을 구현하는 것인데, 이것은 정렬된 셋(Sorted Set)에서 낮은 스코어의 엘리먼트를 원자적인 방식으로 꺼내는(pop) 커맨드이다. 이것은 가장 간단한 구현이다.

    WATCH zset
    element = ZRANGE zset 0 0
    MULTI
    ZREM zset element
    EXEC

`EXEC`가 실패한다면(즉, @nil-reply를 반환하는), 단순히 이 오퍼레이션을 반복하면 된다.

## Redis scripting and transactions

[레디스 스크립트(Redis script)](https://redis.io/commands/eval)는 정의에 따라서는 트랜잭션이 될 수 있으며, 그래서 레디스 트랜잭션으로 할 수 있는 모든 것은 스크립트로도 할 수가 있고, 일반적으로 스크립트가 더 쉽고, 더 빠르다.

이러한 중복은 트랜잭션(Redis transaction)이 이미 오래 전부터 존재해오고 있는 상황에서 스크립트가 레디스 2.6부터 도입되었기 때문이다. 그러나 트랜잭션에 대한 지원을 단기간에 삭제하지는 않을 것 같은데, 왜냐하면 스크립트(Redis scripting)에 의존하지 않더라도 여전히 경쟁 조건을 피할 수는 것이 의미론적으로는 적절하기 때문이다. 특히, 레디스 트랜잭션의 구현 복잡성이 미미하기도 하기 때문이다.

그러나 가능하지 않다. 가깝지 않은 미래에 모든 유저 기반이 스크립트만을 사용하는 것을 보는 것은 불가능하지는 않을 것이다. 만약 그러한 것이 일어난다면, 우리는 트랜잭션을 더 이상 사용하지 않을 것이고, 결국 트랜잭션을 제거할지도 모른다.