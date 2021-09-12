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

The above example shows the usage of the function RedisModule_Init(). It should be the first function called by the module OnLoad function. The following is the function prototype:
위의 예제는 `RedisModule_Init()` 함수의 사용법을 보여준다. 이 함수는 모듈의 `OnLoad` 함수에 의해 첫 번째로 호출되어야 한다. 다음은 함수의 프로토타입니다.

```c
int RedisModule_Init(RedisModuleCtx *ctx, const char *modulename,
                     int module_version, int api_version);
```

`Init` 함수는 레디스 코어에게 모듈의 이름과, 버전 (`MODULE LIST`에서 확인할 수 있는), 그리고 사용하려는 API의 특정 버전에 대해서 알린다.
만약 API 버전이 잘못되었거나, 이름이 이미 사용되고 있거나 또는 비슷한 다른 에러가 있다면, 이 함수는 `REDISMODULE_ERR`를 반환할 것이고, 모듈의 `OnLoad` 함수는 가능한 빨리 에러를 반환할 것이다.
`Init`함수가 호출되기 전에, 호출되는 다른 API 함수는 호출될 수 없으며, 그렇지 않으면 모듈은 세그멘테이션 에러(segfault)가 발생할 것이고, 레디스 인스턴스는 크래시될 것이다.
두 번째로 호출되는 함수 `RedisModule_CreateCommand`는 레디스 코어에 커맨드를 등록하기 위해서 사용된다. 다음은 이 함수의 프로토타입이다.

```c
int RedisModule_CreateCommand(RedisModuleCtx *ctx, const char *name,
                              RedisModuleCmdFunc cmdfunc, const char *strflags,
                              int firstkey, int lastkey, int keystep);
```

보이는 바와 같이, 대부분의 레디스 모둘 API 호출은 모두 첫 번째 인자로 모듈의 컨텍스트를 사용하며, 그것을 호출하는 모듈, 커맨드, 그리고 주어진 커맨드를 클라이언트 등에 대한 참조를 가진다. 
새로운 커맨드를 만들기 위해서, 위의 함수는 컨텍스트, 커맨드의 이름, 커맨드를 구현하는 함수의 포인터, 커맨드의 플래그와 커맨드의 인자 내에서 키 이름에 대한 위치 정보가 필요하다. 

커맨드를 구현하려는 함수는 반드시 아래와 같은 프로토타입을 가져야 한다:

```c
int mycommand(RedisModuleCtx *ctx, RedisModuleString **argv, int argc);
```

이 커맨드 함수의 인수는 다른 모든 API 호출에서 전달되는 컨텍스트, 유저에 의해서 전달되는 커맨드 인수 벡터와 인수의 수로 구성된다.
보는 바와 같이, 인수들은 특정 데이터 타입인 `RedisModuleString`에 대한 포인터로 제공된다. 이것은 구현하려는 API 함수에서 접근하고 사용하기 위한 투명하지 않은 데이터 타입이고, 그래서 직접 그러한 필드들에는 접근할 필요가 전혀 없다.
예저 커맨드 구현을 잘 살펴보면, 우리는 또 다른 호출을 찾을 수 있다.

```c
int RedisModule_ReplyWithLongLong(RedisModuleCtx *ctx, long long integer);
```

이 함수는 `INCR`이나 `SCARD`등과 같은 커맨드들이 하는 것처럼 클라이언트에게 정수를 반환한다.

## Module cleanup

대부분의 케이스에서 특별히 클린업을 할 필요는 없다. 모듈이 언로드될 때, 레디스는 자동적으로 커맨드를 등록해제하고, 알림으로부터 구독을 해제한다. 그러나 모듈이 일부 영구적인 메모리나 설정을 포함하는 경우에, 모듈은 `RedisModule_OnUnload` 함수를 포함할 수도 있다. 만약 모듈이 이 함수를 제공한다면, 언로드 프로세스 중에 호출될 것이다. 다음은 이 함수의 프로토타입이다.

```c
int RedisModule_OnUnload(RedisModuleCtx *ctx);
```

`OnUnload` 함수는 `REDISMODULE_ERR`을 반환함으로써 모듈이 언로딩하는 것을 막게할 수도 있다. 그렇지 않은 경우라면, `REDISMODULE_OK`가 반환되어야 한다.

## Setup and dependencies of a Redis module

레디스 모듈은 레디스나 또 다른 라이브러리에 의존적이지 않으며, 또한 특정한 `redismodule.h` 파일과 함께 컴파일할 필요도 없다. 새로운 모듈을 만들기 위해서 최신 버전의 `redismodule.h` 파일의 소스를 작성할 곳에 복사를 해두기만 하면 되고, 원하는 라이브러리르 모두 링크하고, `RedisModule_OnLoad()` 함수 심볼을 내보내는 동적 라이브러리를 만들면 된다.
모듈은 다른 버전의 레디스에서도 로드할 수 있다.

## Passing configuration parameters to Redis modules

`MODULE LOAD` 커맨드로 모듈을 로드하거나, 또는 redis.conf 파일의 `loadmodule`옵션을 이용할 때, 사용자는 모듈 파일 이름의 뒤에 인수를 추가함으로써 구성 파라미터를 모듈에 전달할 수 있다. 

```
loadmodule mymodule.so foo bar 1234
```

위의 예제에서 문자열 foo, bar, 123은 모듈의 `OnLoad()`함수의 `RedisModuleString` 포인터의 배열로 `argv`에 포함되어 전달될 것이다. 전달되는 인수의 수는 `argc`에 저장된다.
전달받은 문자열들에 접근할 수 있는 방법은 이 문서의 나머지 부분에서 설명될 것이다. 일반적으로 모듈은 구성 파라미터를 특정한 정적 전역 변수에 저장하여 모듈 전체에서 접근할 수가 있으며, 그러한 구성이 다른 커맨드의 행등을 바꿀 수도 있다.

## Working with RedisModuleString objects

모듈 커멘드에 전달될 커맨드 인수 벡터 `argv`와 다른 모듈 APIs 함수의 반환 값은 `RedisModuleString` 타입이다.
보통 직접 모듈 문자열을 다른 API 호출에 직접 전달하지만, 때로는 문자열 오브젝트에 직접 접근할 필요가 있을지 모른다.
문자열 오브젝트에 사용할 수 있는 몇 가지 함수가 있다.

```c
const char *RedisModule_StringPtrLen(RedisModuleString *string, size_t *len);
```

위의 함수는 문자열의 포인터를 반환하고, 길이 정보를 `len`에 설정함으로써 문자열에 접근한다. `const` 포인터 한정자에서 볼 수 있듯, 문자열 오브젝트의 포인터에 작성해서는 안된다.
그렇지만 만약 원한다면, 다음의 API를 이용해서 새로운 문자열 오브젝트를 만들 수도 있다.

```c
RedisModuleString *RedisModule_CreateString(RedisModuleCtx *ctx, const char *ptr, size_t len);
```

위의 커맨드에 의해서 반환하는 문자열은 상응하는 `RedisModule_FreeString` 호출을 이용해서 반드시 해제되어야 한다.

```c
void RedisModule_FreeString(RedisModuleString *str);
```
그러나 문자열 해제 하기를 원치 않는다면, 이 문서의 뒷부분에서 다루는 자동 메모리 관리가 좋은 대안이 될 수 있다.
인수 벡터 `argv`로 전달되는 문자열들은 해제될 필요가 없다. 직접 새롭게 만든 문자열이나, 반환하는 문자열을 반드시 해제해야한다고 명시한 API들의 문자열들만 해제를 하면 된다.

### Creating strings from numbers or parsing strings as numbers

정수로부터 새로운 문자열을 만드는 것은 매우 일반적인 오퍼레이션이기 때문에, 이러한 것을 하는 함수가 있다.

```c
RedisModuleString *mystr = RedisModule_CreateStringFromLongLong(ctx,10);
```

마찬가지로 문자열을 숫자로 파싱하려면 다음과 같이 한다.

```c
long long myval;
if (RedisModule_StringToLongLong(ctx,argv[1],&myval) == REDISMODULE_OK) {
    /* Do something with 'myval' */
}
```

### Accessing Redis keys from modules

사용할만한 대부분의 레디스 모듈은 레디스의 데이터 스페이스와 상호 작용해야 한다(항상 그러한 것은 아닌데, 예를 들어 ID 제너레이터와 같은 것은 절대 레디스 키에 접근하지 않을 것이다). 레디스 모듈은 데이터 스페이스에 접근하기 위한 서로 다른 2가지의 API를 가지고 있다. 하나는 매우 빠르게 접근할 수 있는 저수준의 API이고, 레디스 데이터 구조를 조작하기 위한 함수의 묶음이다. 또 다른 API는 좀 더 고수준이고, 루아 스크립트가 레디스에 접근하는 방법과 비슷하게 레디스 커맨드를 호출하고 결과를 패치하도록 한다.

고수준의 API는 또한 API로는 사용할 수 없는 레디스의 기능들에 접근하기 위해서도 유용하다.

일반적인 모듈에서 개발자들은 저수준의 API를 선호해야 하는데, 저수준 API를 이용해서 구현한 커맨드는 네이티브 레디스 커맨드의 속도와 비슷할만큼 빠른 속도로 실행되기 때문이다. 그러나 분명히 고수준 API에 대한 사용 케이스도 존재한다. 예를 들어, 가끔 보틀넥은 데이터를 처리하고, 접근은 하지 않는 것일 수도 있다.

또한 때때로 저수준 API를 사용하는 것은 고수준의 API를 사용하는 것과 비해 더 어렵지 않기도 하다.

## Calling Redis commands

레디스에 접근하기 위한 고수준 API는 `RedisModule_Call()` 함수와 `Call()`이 반환하는 응답(reply) 객체에 접근하기 위한 함수들을 합한 것이다.
`RedisModule_Call`은 인수로서 함수에 전달할 오브젝트의 타입을 지정하는데 사용하는 포멧 지정자와 함께 특별한 호출 컨벤션을 이용한다.
레디스 커맨드는 커맨드의 이름과 인수의 목록을 이용하는 것만으로 호출된다. 그러나 커맨드를 호출할 때, 인수들은 다른 종류의 문자열들로부터 시작될 수도 있다. 그러한 문자열들로는 널로 종료되는 C문자열, 커맨드 구현 내에서 `argv` 파라미터로부터 받은 `RedisModuleString`, 포인터와 길이를 가지는 바이너리로부터 안전한 C버퍼 등등이 있을 것이다.
예를 들어, 만약 인수 벡터 `argv`에서 받은 `RedisModuleString` 오브젝트 포인터의 배열인 첫 번째 인수(키의 이름)와 숫자 "10"을 표현하는 C문자열인 두 번째 인수(증분)를 이용해서 `INCRBY`를 호출하고 싶다면, 아래와 같은 함수 호출을 이용하게 될 것이다.

```c
RedisModuleCallReply *reply;
reply = RedisModule_Call(ctx,"INCRBY","sc",argv[1],"10");
```

첫 번째 인수는 컨텍스트이고, 두번째는 항상 커맨드 이름으로 사용되는 null로 끝나는 C 문자열이다. 세번째 인수는 포맷 지정자이고 각각의 문자는 뒤따르는 인수들의 타입에 대응한다. 위의 경우에서 "sc"는 `RedisModuleString`오브젝트, 그리고 null로 끝나는 C문자열을 의미한다. 나머지 다른 인수들은 지정한대로 2개의 인수뿐이다. 실제로 `argv[1]`은 `RedisModuleString`이고, "10"은 null로 끝나는 C문자열이다.
다음은 포맷 지정자의 전체 목록이다.

* c -- null로 끝나는 C 문자열의 포인터
* b -- c 버퍼, 두 개의 인수가 필요로하다. C 문자열 포인터와 길이 (size_t)
* s -- `argv` 또는 `RedisModuleString`를 반환하는 다른 레디스 모듈 APIs에 의해 받은 `RedisModuleString`
* l -- Long long integer
* v -- `RedisModuleString` 오브젝트의 배열
* ! -- 이 조정자는 단지 함수에게 리플리카와 AOF로 커맨드를 복제할 것이라는 것을 지시한다. 인수 분석의 관점에서는 무시된다.
* A -- 이 조정자는 `!`이 사용될 때, AOF 전파를 억제할 것을 지시한다. 커맨드는 오직 리플리카로만 전파될 것이다.
* R -- 이 조정자는 `!`이 사용될 때, 리플리카로의 전파를 억제할 것을 지시한다. AOF가 활성화되어 있다면, 커맨드는 AOF로만 전파될 것이다.

이 함수는 성공 시에 `RedisModuleCallReply` 객체를, 실패할 때에는 `NULL`을 반환한다. 
커맨드 이름이 유효하지 않거나, 포맷 지시자가 인식할 수 없는 문자들을 사용하거나, 또는 인수의 수를 잘못 지정해서 커맨드를 실행할 때, `NULL`이 반환된다. 위의 경우에서 `errno` 변수는 `EINVAL`로 설정된다. 클러스터가 활성화된 인스턴스에서 대상 키가 로컬 해시 슬롯의 것이 아닐 때에도 `NULL`이 반환된다. 이 경우에는 `errno`는 `EPERM`이 설정된다.

### Working with RedisModuleCallReply objects

`RedisModuleCall`는 `RedisModule_CallReply*`계열 함수를 사용해서 접근할 수 있는 reply 오브텍트를 반환한다.
타입 또는 응답 (레디스 프로토콜이 지원하는 데이터 타입의 하나에 해당하는)을 획득하기 위해서, `RedisModule_CallReplyType()`함수가 사용된다.

```c
reply = RedisModule_Call(ctx,"INCRBY","sc",argv[1],"10");
if (RedisModule_CallReplyType(reply) == REDISMODULE_REPLY_INTEGER) {
    long long myval = RedisModule_CallReplyInteger(reply);
    /* Do something with myval. */
}
```

유효한 응답 타입은 다음과 같다.

* `REDISMODULE_REPLY_STRING` 대량의 문자열이나 상태의 응답 
* `REDISMODULE_REPLY_ERROR` 에러들
* `REDISMODULE_REPLY_INTEGER` 부호있는 64비트 정수
* `REDISMODULE_REPLY_ARRAY` 응답의 배열
* `REDISMODULE_REPLY_NULL` NULL 응답

Strings, errors and arrays have an associated length. For strings and errors the length corresponds to the length of the string. For arrays the length is the number of elements. To obtain the reply length the following function is used:

```c
size_t reply_len = RedisModule_CallReplyLength(reply);
```

In order to obtain the value of an integer reply, the following function is used, as already shown in the example above:

```c
long long reply_integer_val = RedisModule_CallReplyInteger(reply);
```

Called with a reply object of the wrong type, the above function always returns LLONG_MIN.
Sub elements of array replies are accessed this way:

```c
RedisModuleCallReply *subreply;
subreply = RedisModule_CallReplyArrayElement(reply,idx);
```

The above function returns NULL if you try to access out of range elements.
Strings and errors (which are like strings but with a different type) can be accessed using in the following way, making sure to never write to the resulting pointer (that is returned as as const pointer so that misusing must be pretty explicit):

```c
size_t len;
char *ptr = RedisModule_CallReplyStringPtr(reply,&len);
```

If the reply type is not a string or an error, NULL is returned.
RedisCallReply objects are not the same as module string objects (RedisModuleString types). However sometimes you may need to pass replies of type string or integer, to API functions expecting a module string.
When this is the case, you may want to evaluate if using the low level API could be a simpler way to implement your command, or you can use the following function in order to create a new string object from a call reply of type string, error or integer:

```c
RedisModuleString *mystr = RedisModule_CreateStringFromCallReply(myreply);
```

If the reply is not of the right type, NULL is returned. The returned string object should be released with RedisModule_FreeString() as usually, or by enabling automatic memory management (see corresponding section).

## Releasing call reply objects

### Returning values from Redis commands

### Returning arrays with dynamic length

## Arity and type checks

### Low level access to keys

### Getting the key type

### Creating new keys

### Deleting keys

### Managing key expires (TTLs)

### Obtaining the length of values

### String type API

### List type API

### Set type API

### Sorted set type API

### Hash type API

### Iterating aggregated values

## Replicating commands

## Automatic memory management

## Allocating memory into modules

### Pool allocator

## Writing commands compatible with Redis Cluster