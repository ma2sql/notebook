
## NETWORK

#### timeout
- 기본값: 0 (seconds)

클라이언트가 N초동안 유휴(idle)상태라면, 커넥션을 종료시킨다. `0`으로 설정하면 이 기능을 비활성화한다.

#### tcp-keepalive
- 기본값: 300 (seconds)

TCP keepalive 관련 설정.
이 값이 0이 아니라면, 커뮤니케이션이 없는 상태의 클라이언트에게 `TCP ACKs`를 보내기 위해서 `SO_KEEPALIVE`를 사용한다. 이것은 다음의 2가지 이유로 유용하다.

1. 연결이 죽어있는 상태를 발견한다.
2. 네트워크 장비 관점에서 커넥션이 살아있는지를 확인한다.

리눅스에서 지정된 값은 `ACKs` 전송에 대한 간격으로 사용된다. 커넥션을 종료시키기 위해서 2배의 시간이 필요하다. 다른 커널에서 이 간격은 커널 설정에 의존적이다.

이 옵션에 대해서 합리적인(reasonable) 값은 300초인데, 레디스 3.2.1버전에서부터 새로운 레디스의 기본값으로 지정되었다.


### ADVANCED CONFIG
```
The client output buffer limits can be used to force disconnection of clients
# that are not reading data from the server fast enough for some reason (a
# common reason is that a Pub/Sub client can't consume messages as fast as the
# publisher can produce them).
#
# The limit can be set differently for the three different classes of clients:
#
# normal -> normal clients including MONITOR clients
# replica  -> replica clients
# pubsub -> clients subscribed to at least one pubsub channel or pattern
#
# The syntax of every client-output-buffer-limit directive is the following:
#
```
클라이언트 출력 버퍼(client output buffer) 제한은 클라이언트 커넥션을 강제로 종료시키기 위해 사용될 수 있다.

#### client-output-buffer-limit
- 기본값:
    - normal 0 0 0
    - replica 256mb 64mb 60
    - pubsub 32mb 8mb 60