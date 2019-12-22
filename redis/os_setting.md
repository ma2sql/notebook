# Redis를 운영하기 위해 필요한 OS 관련 옵션

## vm.swappiness
swap_tendency 를 지정하는 옵션

```
swap_tendency = mapped_ratio/2 + distress + vm_swappiness
```
swappiness=0의 의미
- Linux 3.5 이상에서, swapping을 완전히 비활성화하는 것을 의미
- Linux 3.4 까지는 OOM을 피하기 위한 경우에만 swap
Redis에서는 우선 swappiness를 피할 수 있도록 노력해야한다. RAM이 충분하지 않을 때, Redis는 swappiness를 사용할 수 있는데, OOM으로 레디스가 죽는 것이 swappiness사용으로 인해 레디스가 느려지는 것보다는 낫다. HA 구성으로 빠르게 페일오버가 될 수 있으니까. 그래서 이 값은 **0**이 권장된다.


## vm.overcommit_memory
참고: https://brunch.co.kr/@alden/16

**memory commit**: 프로세스가 커널에게 malloc 을 통해 메모리 할당을 요청하고, 커널은 메모리 영역에 대한 주소를 프로세스에게 다시 전달하지만, 실제로는 메모리 할당이 이루어지지 않은 상태

그렇다면 **over commit** 이 필요한 이유는?
fork와 같이 순간적으로 많은 양의 메모리가 필요한 상황이 있기 때문이다.

지정 가능한 옵션
- 0: Heuristic. 사용 가능한 메모리가 남아 있을 때 성공 리턴 (Page Cache + Swap + Slab reclaimable)
- 1: 항상 성공을 리턴
- 2: Swap 영역 크기 + (물리메모리 x vm.overcommit_ratio) 이내일 때, 성공을 리턴

## net.core.somaxconn
listen()으로 바인딩 된 서버 소켓에서 accept()를 기다리는 소켓 개수에 관련된 커널 파라미터는 **net.core.somaxconn**

## net.ipv4.tcp_max_syn_backlog
SYN_RECEIVED 상태의 소켓(즉, connection incompleted)을 위한 queue

## net.core.netdev_max_backlog
각 네트워크 장치 별로 커널이 처리하도록 쌓아두는 queue의 크기

## Transparent Huge Pages (THP)
jmelloc의 영향일까?
forking할 때, 부모 프로세스와 공유하는 메모리 영역이 Huge Page로 전환된다.
https://redis.io/topics/latency#latency-induced-by-transparent-huge-pages
https://blog.digitalocean.com/transparent-huge-pages-and-alternative-memory-allocators/
https://cachecloud.github.io/2017/02/16/Redis%E7%9A%84Linux%E7%B3%BB%E7%BB%9F%E4%BC%98%E5%8C%96/#chapter3
https://gist.github.com/shino/5d9aac68e7ebf03d4962a4c07c503f7d
http://antirez.com/news/84
https://github.com/jemalloc/jemalloc/issues/243
https://jemalloc-discuss.canonware.narkive.com/iDzJEOI8/huge-page-support-would-be-useful-in-jemalloc
https://discuss.aerospike.com/t/disabling-transparent-huge-pages-thp-for-aerospike/5233
https://news.ycombinator.com/item?id=8551756


# Reference
- https://redis.io/topics/admin
- https://www.slideshare.net/janghoonsim/kvm-performance-optimization-for-ubuntu
- http://www.cubrid.com/faq/3794713
- https://meetup.toast.com/posts/54
- https://brunch.co.kr/@alden/14


## command

```
ps -C redis-server -o COLUMNS
hexdump -C dump.rdb | head -n1
```