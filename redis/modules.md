# Redis Modules: an introduction to the API

모듈(Redis Modules) 문서는 다음과 같이 구성된다:

* 모듈에 대한 소개 (이 문서). 레디스 모듈 시스템과 API에 대한 개요를 다룬다. 이 문서를 읽기 시작하는 것은 좋은 생각이다.
* [Implementing native data types](https://redis.io/topics/modules-native-types)는 네이티브 데이터 타입을 모듈로 구현하는 것을 다룬다.
* [Blocking operations](https://redis.io/topics/modules-blocking-ops)는 블로킹 커맨드를 작성하는 방법을 보여준다. 블로킹 커맨드란 곧바로 응답을 하지 않지만, 레디스 서버를 블로킹하지 않은 상태에서 클라이언트를 블로킹하고, 가능해질 때 응답을 하는 커맨드이다.
* [Redis modules API reference](https://redis.io/topics/modules-api-ref)는 `RedisModule` 함수들의 `module.c`내의 위쪽 주석으로부터 만들어진다. 각각의 함수가 어떻게 동작하는지 이해하기 위한 좋은 자료가 될 것이다.

Redis 모듈을 사용하면 외부 모듈을 사용하여 Redis 기능을 확장할 수 있고 코어 내부에서 수행될 수 있는 것과 유사한 기능을 가지는 새로운 Redis 명령을 신속하게 구현할 수 있습니다.

레디스 모듈은 동적 라이브러리로, 시작 시점이나 또는 `MODULE LOAD` 커맨드를 이용해서 로드될 수 있다. 레디스는 C API를 내보대는데, redismodule.h 이라고 불리는 단일 C 해더 파일 형식이다. 모듈은 C로 작성되어야 하지만, C++나 다른 언어들과 같이 C 바인딩 기능을 가지는 언어를 사용하는 것은 가능하다.

모듈은 다른 버전의 레디스에도 로드될 수 있도록 디자인되었다. 그래서 특정 레디스 버전에서 실행하려고 주어진 모들을 설계하거나 다시 컴파일할 필요가 없다. 이러한 이유로, 모듈은 특정 API 버전을 이용해서 레디스 코어에 등록된다. 현재의 API 버전은 "1" 이다.

이 문서는 레디스 모듈의 알파 버전에 대한 것이다. API와 기능, 그리고 다른 세부 사항들은 미래에 변경될 수도 있다.

## Loading modules

개발하고 있는 모듈을 테스트하기 위해서, 다음과 같이 redis.conf 옵션을 이용해서 모듈을 로드할 수 있다.

```
loadmodule /path/to/mymodule.so
```

아래의 커맨드를 이용해서 런타임 중에 모듈을 로드하는 것 또한 가능하다.

```
MODULE LOAD /path/to/mymodule.so
```

로드된 모든 모듈 목록을 보기 위해서는 아래와 같이 한다:

```
MODULE LIST
```

마지막으로, 아래의 커맨드를 이용해서 모듈을 언로드할 수도 있다. (그리고 나중에 원하는 시점에 다시 로드할 수도 있는)

```
MODULE UNLOAD mymodule
```

위의 `mymodule`은 .so 접미사가 빠진 파일 이름이 아니고, 대신 모듈 자신을 레디스 코어로 등록하기 위해서 사용한 이름이다. 이 이름은 `MODULE LIST`를 사용해서 알 수 있다. 그러나 동적 라이브러리의 파일 이름을 모듈 자신을 레디스 코어에 등록하려고 사용한 이름과 같은 것으로 하는 것은 좋은 습관이다.

## The simplest module you can write

모듈의 다른 부분들을 보여주기 위해서, 여기 매우 단순한 모듈 예제가 있고, 이것은 랜덤한 숫자를 출력하는 커맨드의 구현을 보여준다.

```c
#include "redismodule.h"
#include <stdlib.h>

int HelloworldRand_RedisCommand(RedisModuleCtx *ctx, RedisModuleString **argv, int argc) {
    RedisModule_ReplyWithLongLong(ctx,rand());
    return REDISMODULE_OK;
}

int RedisModule_OnLoad(RedisModuleCtx *ctx, RedisModuleString **argv, int argc) {
    if (RedisModule_Init(ctx,"helloworld",1,REDISMODULE_APIVER_1)
        == REDISMODULE_ERR) return REDISMODULE_ERR;

    if (RedisModule_CreateCommand(ctx,"helloworld.rand",
        HelloworldRand_RedisCommand, "fast random",
        0, 0, 0) == REDISMODULE_ERR)
        return REDISMODULE_ERR;

    return REDISMODULE_OK;
}
```

이 모듈 예제에는 2개의 함수가 있다. 그 중 하나는 `HELLOWORLD.RAND`라는 커맨드를 구현하고 있다. 이 함수는 이 모듈을 위한 특별한 것이다. 그러나 다른 함수 `RedisModule_OnLoad()`는 각각의 레디스 모듈에서 반드시 존재해야 한다. 이것은 모듈을 초기화해서 커맨드로 등록하고, 잠재적으로 모듈이 사용할 개별적인 데이터 구조를 위한 진입점이다.

모듈이 `HELLOWORLD.RAND`와 같이 모듈의 이름 뒤에 점(.)을 붙이고, 마지막에 커맨드 이름을 붙여서 커맨드를 호출하도록 하는 것은 좋은 생각이다. 이렇게 하면 충돌이 발생할 가능성이 줄어들 것이다.

만약 다른 모듈이 충돌하는 커맨드를 가지는 경우에는 `RedisModule_CreateCommand` 함수가 모듈 중 하나에서 실패하고, 모듈의 로딩은 에러를 반환하며 중단될 것이기 때문에, 레디스에서 동시에 동작할 수는 없을 것이다.

## Module initialization