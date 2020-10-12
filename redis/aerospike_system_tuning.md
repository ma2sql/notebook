# How to tune the Linux kernel for memory performance

##Context

The linux kernel attempts to optimize RAM utilization, in that it occupies unused RAM with caches. This is done on the basis that unused RAM is wasted RAM.

리눅스 커널은 RAM사용을 최적화하려는 시도를 하며, 그렇기 때문에 사용되지 않는 RAM을 캐시로 점유하려고 한다. 이것은 사용되지 않는 RAM은 낭비되는 RAM이라는 것에 기반한다.

Over time the kernel will fill the RAM with cache. As more memory is required by the applications/buffers, the kernel goes through the cache memory pages and finds a block large enough to fit the requested malloc. It then frees that memory and allocates it to the calling application.
지난 시간동안 커널은 RAM을 캐시로 채웠다. 어플리케이션으로부터 더 많은 메모리를 요구받을 때, 커널은 캐시 메모리 페이지를 통해서 충분한 수의 메모리를 확보한다. 그리고 나서 메모리는 해제될 것이고, 호출하는 어플리케이션에 메모리를 할당해줄 것이다.

Under some circumstances, this can affect the general performance of the system as cache de-allocation is time-consuming in comparison with access to unused RAM. Higher latency could therefore sometimes be observed.
어떤 환경 아래에서는 이것은 캐시 해제 시스템에 대한 전반적인 성능에 영향을 끼치는데, 사용하지 않는 RAM에 접근하는 것보다 더 많은 시간을 소모하는.. 더 높은 레이턴시가 때때로 관측되기도 한다.

This latency will purely be based on the fact that RAM is being used to its full speed potential. As such, no other symptoms may occur apart from general overall and potentially sporadic latency increases. The equivalent would be similar to symptoms that may be observed if the hard disks are not keeping up with reads and writes. The latency may also affect either Aerospike, or operating system components, such as network card/iptables/ebtables/iproute2 mallocs. As such this may show network-based latency instead. The following article discusses this further and provides steps to minimize impact on the system.

## Explanation

The kernel memory cache contains the following:
커널 메모리 캐시는 다음을 포함한다.

* dirty cache - Data blocks not yet committed to the file systems which support caching (e.g. ext4). This can be emptied by issuing the sync command athough this may imply a periodic performance penalty. This is not advised for normal usage unless it is extremely important to commit data to hard drive (for example when expecting a failure).
* 더티 캐시 (dirty cache): (ext4와 같이 캐시를 지원하는) 파일시스템으로 아직 커밋되지 않은 데이터 블럭. 이 캐시는 sync 커맨드를 발행함으로써 비워질 수 있는데, 간헐적인 성능상의 불이익을 내포할 수도 있다. 이것은 데이터를 하드 디스크 드라이브로 커밋하는 것이 매우 중요하지 않다면 일반적인 사용에서는 추천되지 않는다. (예를 들어, 고장이 예상되는 경우 등등) 

* clean cache - Data blocks which are on the hard drive but are also retained in memory for fast access. Dropping the clean cache can result in a performance deficit as all data will read from disk, whereas beforehand, the frequently used data would be fetched directly from RAM.
* inode cache - Cache of the inode location information. This can be dropped as with clean cache but with the attendant performance penalty.
* slab cache - This type of cache stores objects allocated via malloc by applications so that they may be re-malloc again in the future with object data already populated, resulting in speed gain during memory allocations.
While not much can be done with dirty cache, the other cached objects can be cleared. This has potentially 2 outcomes. Latency in high-malloc applications, such as Aerospike when storing data in memory, will be reduced. On the other hand, disk access may slow down, as all data will have to be read from disk.

Clearing slab cache on a server can potentially introduce a temporary speed penalty (spike). For this reason, it is not advised to clear caches. Instead, it is preferred to inform the system that a certain amount of RAM should never be occupied by cache.

If necessary, clearing the cache can be performed as follows:

```
# clear page cache (above type 2 and 3)
$ echo 1 > /proc/sys/vm/drop_caches
```
```
# clear slab cache (above type 4)
$ echo 2 > /proc/sys/vm/drop_caches
```
```
# clear page and slab cache (types 2,3,4)
$ echo 3 > /proc/sys/vm/drop_caches
```
Most of the space will be occupied by page cache, not slab cache. It is recommended that when clearing cache, to only drop the page cache (echo 1).

For a more permanent fix, a minimum number of free RAM can be set for the kernel. Consider the following example:
```
Total RAM: 100GB
Used: 10GB
Buffers: 40GB
Minimum free: 10GB
Cache: 40GB
```
In this example, there is 10GB free memory selected using the minimum free option. In such a case, if 5GB of memory is allocated for buffers, the kernel will allow the allocation to happen instantly. It will then de-allocate some cache to ensure 10GB free memory. Allocations will happen instantly and cache will be dynamically shrunk to ensure that 10GB remains free at all times. The new allocation would look as follows:
```
Total RAM: 100GB
Used: 10GB
Buffers: 45GB
Minimum free: 10GB
Cache: 35GB
```
Fine-tuning these parameters is dependant upon the current utilization. For Aerospike, it should be at least 1.1GB free in min_free_kbytes, if the available system memory allows. This means that caches will still operate sufficiently, while leaving a margin for applications to allocate into.
```
$ cat /proc/sys/vm/min_free_kbytes
67584
```
Tuning is performed by performing an echo NUMBER > /proc/sys/vm/min_free_kbytes where, NUMBER is the number of kilobytes required to be free in the system. To leave 3% of memory on a 100GB RAM machine unoccupied, the command would be:
```
echo 3145728 > /proc/sys/vm/min_free_kbytes
```
Aerospike advise to leave at least 1.1GB of RAM to min_free_kbytes, i.e. 1153434.

On a system with over 37GB of total RAM, you should leave no more than 3% of spare memory to min_free_kbytes in order to avoid the kernel spending too much time unnecessarily reclaiming memory. This would equal anywhere between 1.1GB and 3% of total RAM on such systems.

Caution should be exercised when setting this parameter, both too low and too high values can have an adverse effect upon system performance. Setting min_free_kbytes too low prevents the system from reclaiming memory. This can result in system hangs and OOM kills of processes.

Setting this parameter to a value that is too high (5-10% of total system memory) will cause the system to run out of memory immediately. Linux is designed to use all available RAM to cache file system data. Setting a high min_free_kbytes value results in the system spending too much time reclaiming memory.

The standard RedHat recommendation 211 is to keep min_free_kbytes at 1-3% of the total memory on the system, with Aerospike advising to keep at least 1.1GB, even if that is above the official recommended total memory percentage.

It is advised to either reduce swappiness to 0 or not use swap. For low-latency operations, using swap to any extent will drastically slow down performance.

To set the swappiness to 0 to reduce potential latency:
```
echo 0 > /proc/sys/vm/swappiness
```
## Notes

> IMPORTANT: Any and all changes above are NOT permanent. They only happen during machine runtime. To make the changes permanent, additions must be made to /etc/sysctl.conf.

The following lines make the changes shown above permanent:
```
vm.min_free_kbytes = 1153434
vm.swappiness = 0
```
As always, editing such parameters can be destructive if done incorrectly. It is recommended to perform the changes in a lab environment before moving to production. Making changes dynamically before performing permanent change helps in mitigating any potential side effects which could occur.

There is another parameter aimed at a similar output as the above, called zone_reclaim. Unfortunately, this parameter causes aggressive reclaims and scans and should therefore be disabled. This is disabled as standard on all newer kernels and distributions.

The following command can be used to ensure that zone_reclaim is disabled:
```
$ sysctl -a |grep zone_reclaim_mode
vm.zone_reclaim_mode = 0
```