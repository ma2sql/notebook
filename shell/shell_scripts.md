# 자주 사용하는 스크립트

# Table Of Content
<!-- TOC -->

- [자주 사용하는 스크립트](#자주-사용하는-스크립트)
- [Table Of Content](#table-of-content)
    - [Swap 사용량 조사](#swap-사용량-조사)
    - [redis 서버의 swap 사용량](#redis-서버의-swap-사용량)

<!-- /TOC -->

## Swap 사용량 조사
```
(echo "COMM PID SWAP"; 
    for file in /proc/*/status ; do 
        awk '/^Pid|VmSwap|Name/{printf $2 " " $3 "\n"}' $file; 
    done | grep kB | grep -wv "0 kB" | sort -k 3 -n -r \
) | column -t
```

## redis 서버의 swap 사용량
```
(echo "PID COMM SWAP(KB)";
for REDIS_PID in $(pgrep -f redis-server); do 
    REDIS_NAME=$(cat /proc/${REDIS_PID}/cmdline | sed 's/\s//g')
    VM_SWAP=$(awk '/VmSwap/ { print $2 }' /proc/${REDIS_PID}/status)
    echo ${REDIS_PID} ${REDIS_NAME} ${VM_SWAP}
done | awk '{print $NF, $0}' | sort -nr | cut -f2- -d' ') | column -t
```