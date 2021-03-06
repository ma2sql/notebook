---
tags: [redis, os, shell]
---

# 1. 자주 사용하는 스크립트

<!-- TOC -->

- [1. 자주 사용하는 스크립트](#1-자주-사용하는-스크립트)
  - [1.1. Swap 사용량 조사: 1](#11-swap-사용량-조사-1)
  - [1.2. Swap 사용량 조사: 2](#12-swap-사용량-조사-2)
  - [1.3. redis 서버의 swap 사용량](#13-redis-서버의-swap-사용량)
  - [2.1 초단위로 /proc/meminfo 출력하기](#21-초단위로-procmeminfo-출력하기)

<!-- /TOC -->

## 1.1. Swap 사용량 조사: 1
```
(echo "COMM PID SWAP"; 
    for file in /proc/*/status ; do 
        awk '/^Pid|VmSwap|Name/{printf $2 " " $3 "\n"}' $file; 
    done | grep kB | grep -wv "0 kB" | sort -k 3 -n -r \
) | column -t
```

## 1.2. Swap 사용량 조사: 2
*https://blog.sleeplessbeastie.eu/2016/12/26/how-to-display-processes-using-swap-space/*
```bash
find /proc -maxdepth 2 -path "/proc/[0-9]*/status" -readable \
-exec awk -v FS=":" '{
    process[$1]=$2;
    sub(/^[ \t]+/,"",process[$1]);
} END {
    if(process["VmSwap"] && process["VmSwap"] != "0 kB") {
        printf "%10s %-30s %20s\n",process["Pid"],process["Name"],process["VmSwap"]
}}' '{}' \; \
 | awk '{print $(NF-1),$0}' | sort -h | cut -d " " -f2-
```

## 1.3. redis 서버의 swap 사용량
```
(echo "PID COMM SWAP(KB)";
for REDIS_PID in $(pgrep -f redis-server); do 
    REDIS_NAME=$(cat /proc/${REDIS_PID}/cmdline | sed 's/\s//g')
    VM_SWAP=$(awk '/VmSwap/ { print $2 }' /proc/${REDIS_PID}/status)
    echo ${REDIS_PID} ${REDIS_NAME} ${VM_SWAP}
done | awk '{print $NF, $0}' | sort -nr | cut -f2- -d' ') | column -t
```

## 2.1 초단위로 /proc/meminfo 출력하기
```
while true; do 
    NOW=$(date '+%Y-%m-%d %H:%M:%S'); 
    cat /proc/meminfo \
        | grep -E '((In)?[aA]ctive\((anon|file)\)|Swap(Cached|Free)|Dirty):' \
        | xargs echo \
        | sed "s/^/[$NOW] /";  
        sleep 1; 
done;
```