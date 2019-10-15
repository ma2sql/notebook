---
tags: [redis]
---

## AOF 파일로부터 expiry를 제거하기
expire 관련 설정은 AOF 파일 내에서는 `PEXPIREAT`으로 표현된다. 따라서, 여러 라인에 대한 정규식 검사를 통해, expire 설정을 제거하는 것이 가능하다.
```
pcregrep -v -M '^\*3\r\n\$9\r\nPEXPIREAT\r\n\$[0-9]+\r\n.+\r\n\$[0-9]+\r\n[0-9]+' __AOF_FILE__ \
    | redis-cli -p __PORT__ --pipe 
```

### script effects replication
5.0 이전에는, 기본적으로 EVAL 커맨드 실행이 AOF 파일 내에 스크립트와 인자가 그대로 남게 된다. 즉, lua script 내에서는 expire 관련 커맨드를 실행한다면 `PEXPIREAT` 이 아닌 실행한 커맨드 그대로 남긴다. 3.2 부터는 EVAL 스크립트가 아닌, EVAL에 의해 변경된 데이터 분에 대해서만 기록을 하게 하는 옵션(script effects replication) 이 추가되었다. 아래 옵션을 스크립트 내에서 write 관련 커맨드보다 앞에 위치시키면 된다. 5.0부터는 script effects replication가 기본적으로 활성화되어 있다.

```
redis.replicate_commands() -- Enable effects replication.
```

*https://redis.io/commands/eval#replicating-commands-instead-of-scripts*

```
### redis 4.0

# Disable effects replication.
eval "redis.call('SET', KEYS[1], ARGV[1]); redis.call('expire', KEYS[1], 10000);" 1 foo bar
...
*5
$4
eval
$74
redis.call('SET', KEYS[1], ARGV[1]); redis.call('expire', KEYS[1], 10000);
$1
1
$3
foo
$3
bar

# Enable effects replication
eval "redis.replicate_commands(); redis.call('SET', KEYS[1], ARGV[1]); redis.call('expire', KEYS[1], 10000);" 1 foo bar
...
*1
$5
MULTI
*3
$3
SET
$3
foo
$3
bar
*3
$9
PEXPIREAT
$3
foo
$13
1570828236175
*1
$4
EXEC
```