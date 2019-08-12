- [APPEND ONLY MODE](#append-only-mode)
    - [appendonly](#appendonly)
    - [appendfilename](#appendfilename)
    - [appendfsync](#appendfsync)
    - [no-appendfsync-on-rewrite](#no-appendfsync-on-rewrite)
    - [auto-aof-rewrite-percentage](#auto-aof-rewrite-percentage)
    - [auto-aof-rewrite-min-size](#auto-aof-rewrite-min-size)
    - [aof-load-truncated](#aof-load-truncated)
    - [aof-use-rdb-preamble](#aof-use-rdb-preamble)

## APPEND ONLY MODE

### appendonly
- 지정 가능한 값: {yes|no}
- 기본값: no

기본적으로 redis는 데이터셋을 디스크에 비동기적으로 덤프한다. 이러한 것은 많은 어플리케이션에서 충분히 좋은 모습을 보여주지만,
redis의 프로세스 또는 전원의 장애로 인해 몇 분간의 write 데이터 손실을 초래할 수 있다.
`Append Only`는 좀 더 견고한 영속성을 제공하는 모드이다. 
예를 들어, fsync정책(everysec)을 디폴트로 사용하는 경우에는 대략 1초간의 데이터 손실만이 있을 뿐이다.
(서버 전원에 문제가 발생하거나, os는 유지되는 상황에서, redis 프로세스에만 문제가 발생한다면 단 한건의 write 손실이 발생할 것)
AOF와 RDB 영속성을 동시에 활성화해도 문제가 없다. 만약 서버 시작 시점에 AOF가 활성화되어 있다면, Redis는 AOF 파일을 우선적으로 읽을 것이다.
AOF가 좀더 견고함을 보장하기 때문이다.
ref: http://redis.io/topics/persistence for more information.

### appendfilename
- 지정 가능한 값: 문자열
- 기본값: appendonly.aof

append only file의 이름.  `dir`로 지정된 디렉터리 내에 `appendfilename` 지정된 이름의 파일이 생성된다.


### appendfsync
- 지정 가능한 값: {always|everysec|no}
- 기본값: no
- ref: http://antirez.com/post/redis-persistence-demystified.html

fsync() 시스템콜은 OS에게 실제 데이터의 쓰기를 디스크에까지 이어지도록 요청한한다.
일부 OS는 실제 디스크로 데이터를 플러시하고, 일부 다른 OS는 그저 ASAP으로 플러시를 시도한다.

Redis 에서는 다음의 3가지의 fsync 관련 모드를 지원한다.
- no: fsync를 수행하지 않는다. 그저 OS에 의해 flush가 진행되도록 맡긴다. 가장 빠르다.
- always: 매 write마다 fsync를 수행한다. 느리지만 가장 안전하다.
- everysec: fsync는 오직 1초마다 한번씩만 수행된다. 절충안.

디폴트는 `everysec`로, 일반적으로는 성능과 안정성의 올바른 타협점이다.
당신의 이해에 달렸는데, 만약 `no`를 선택한다면 좀 더 편해질 수 있다. 왜냐하면 fsync를 OS에게 맡김으로써, fsync 횟구가 줄어들어 좀 더 나은 성능을 보여줄거니까. (다만, 좀 더 데이터가 손실되어도 좋다면 RDB를 써도 좋겠지...) 아니면 반대로, `always`를 선택하면 많이 느리겠지만 everysecc보다도 더 안정성을 가질 수 있을 것이다.

확신이 없다면, `everysec`을 쓰세요.

### no-appendfsync-on-rewrite
- 지정 가능한 값: {yes|no}
- 기본값: no

AOF 정책이 `always` 또는 `everysec`일 때, 백그라운드 저장 프로세스가 I/O를 많이 발생시키며 실행될 때 (BGSAVE or BGREWRITEAOF), 일부 리눅스 설정에서 Redis는 너무 긴 fsync 요청에 대해서는 아마 블로킹을 할 것이다.
현재도 수정되지 않았다는 것을 알아두세요. 심지어는 다른 스레드 fsync를 수행하는 것에도 블로킹이 될 것이다.

이러한 문제를 해결하기 위해, 다음의 옵션으로 fsync를 방지할 수 있다. 메인 프로세스로부터
BGSAVE 또는 BGREWRITEAOF가 실행중이라면..

이것은 다른 자식 프로세스가 save할 때, redis의 영속성은 appendfsync none과 같이 된다.
실제적으로, 이것은 최대 30초 간의 데이터를 손실할 수 있다 (최악의 경우, linux 기본 설정)

만약 레이턴시 쪽에서 문제를 겪고 있다면 이 옵션을 yes로, 그렇지 않다면 no로 두어 영속성 관점에서 가장 안정적인 옵션으로서 운영하면 좋다.


### auto-aof-rewrite-percentage
- 지정 가능한 값: 0-100
- 기본값: 100

자동으로 AOF파일을 재작성한다.
Redis는 묵시적인 BGREWRITEAOF 요청을 자동으로 발생시켜, AOF파일을 재작성할 수 있다. AOF 로그 사이즈가 지정된 퍼센테이지가 도달하는 경우.

이것은 어떻게 동작할까?
Redis는 AOF파일의 사이즈를 기억하는데, 가장 최근의 rewrite사이즈 (만약 rewrite가 없었다면, 재시작 이후 AOF가 시작되었을 때의 사이즈가 사용된다.)

이 기준이 되는 사이즈는 현재의 사이즈와 비교된다. 만약 현재의 사이즈가 지정된 퍼센테이지보다 크다면, rewrite가 트리거된다. 물론 필요에 의해 rewrite되기 위해 필요한 최소 사이즈를 지정하는 것도 가능하다. rewrite하기에는 파일 사이즈가 매우 작을 때에 이 옵션은 도움이 될 수 있다.

0으로 지정하면, AUTO AOF Rewrite 기능은 비활성화된다.

auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

### auto-aof-rewrite-min-size
- 지정 가능한 값: size...
- 기본값: 64mb

[auto-aof-rewrite-percentage](#auto-aof-rewrite-percentage) 설명을 참고


### aof-load-truncated
- 지정 가능한 값: {yes|no}
- 기본값: yes

Redis가 시작되는 시점에, AOF 데이터를 디스크에서 메모리로 로드하는 과정 중에서, AOF file의 마지막 부분이 불완전한 상태인지를 알 수 있다. Redis 프로세스가 운영중 크래시될 때 발생할 수 있고, 특히 ext4 파일 시스템이 data=ordered 옵션없이 마운트 되었을 때
(하지만 Redis가 크래시되거나 중단되었을 때, OS가 아직 정상적으로 동적하고 있다면 발생하지 않을 수도 있다)

불완전할 AOF 파일임을 알아차렸을 때, Redis는 에러를 발생시키며 종료되거나 또는, 가능한만큼 데이터를 로드한 다음 Redis를 시작한다. 이 옵션으로 이러한 동작 여부를 지정할 수 있다.

만약 **yes**로 지정된다면, 불완전한 AOF 파일은 그대로 로드될 것이고, redis 서버는 불완전한 로그에 대해서는 생략한채 시작될 것이다. 반대로 **no**로 지정되는 경우에는 redis는 에러를 출력하며 시작은 시작되지 않을 것이다. 그리고 사용자는 `redis-check-aof`툴을 이용해서 AOF 파일을 수정한 다음, 다시 redis를 시작해볼 수 있다.

참고하세요. AOF 파일의 중간 부분이 불완전할 경우에도 서버는 여전히 에러를 발생시키며 종료될 것이다. 이 옵션은 오직 적용되는데 Redis가 AOF 파일로부터 더 많은 파일을 읽으려고 시도 할때, 하지만 충분한 바이트를 발견하지 못했을 때...
이것을 `redis-check-aof`로 수정하려고 할때, 손상된 이후의 데이터는 모두 삭제될 것이다.
http://redisgate.kr/redis/configuration/param_aof-load-truncated.php


### aof-use-rdb-preamble
- 지정 가능한 값: {yes|no}
- 기본값: yes

AOF 파일을 재작성할 때, Redis는 ***RDB preamble***을 이용하여 더 빠르게 쓰고 복구할 수 있다.
이 옵션이 활성화되어 있다면, AOF파일을 재작성하는 작업은 다음 두 가지 스탠자(구)로 구성된다.
```
[RDB file][AOF tail]
```
로딩 중, Redis는 AOF 파일이 "REDIS"라는 문자열로 시작한다면 알아차리고, 고정된 앞 부분은 RDB 파일로 로드하고, 계속해서 뒷 부분은 AOF파일로 로드한다.