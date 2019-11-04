## fix_slots_coverage
- 슬롯 커버리지를 확인하고 수정하는 메서드
- 픽스 대상 케이스
    1. (none) slot이 할당 또는 해당 slot에 대한 키를 보유한 노드가 없는 경우
    2. (single) slot이 할당되지는 않았지만, 해당 slot에 대한 키를 보유한 노드가 있는 경우
    3. (multi) slot이 할당되지는 않았지만, 해당 slot에 대한 키를 보유한 노드가 2개 이상인 경우
- **master,fail** 상태라면, 먼저 `CLUSTER FORGET` 을 실행할 필요가 있음
```ruby
>>> Covering slot 5461 with 192.168.56.101:6379
/Redis/ruby/lib/ruby/gems/2.4.0/gems/redis-3.3.3/lib/redis/client.rb:121:in `call': ERR Slot 5461 is already busy (Redis::CommandError)
        from /Redis/ruby/lib/ruby/gems/2.4.0/gems/redis-3.3.3/lib/redis.rb:2705:in `block in method_missing'
        from /Redis/ruby/lib/ruby/gems/2.4.0/gems/redis-3.3.3/lib/redis.rb:58:in `block in synchronize'
        from /Redis/ruby/lib/ruby/2.4.0/monitor.rb:214:in `mon_synchronize'
        from /Redis/ruby/lib/ruby/gems/2.4.0/gems/redis-3.3.3/lib/redis.rb:58:in `synchronize'
        from /Redis/ruby/lib/ruby/gems/2.4.0/gems/redis-3.3.3/lib/redis.rb:2704:in `method_missing'
        from /Redis/RedisHome/bin/redis-trib.rb:471:in `block in fix_slots_coverage'
        from /Redis/RedisHome/bin/redis-trib.rb:468:in `each'
        from /Redis/RedisHome/bin/redis-trib.rb:468:in `fix_slots_coverage'
        from /Redis/RedisHome/bin/redis-trib.rb:406:in `check_slots_coverage'
        from /Redis/RedisHome/bin/redis-trib.rb:369:in `check_cluster'
        from /Redis/RedisHome/bin/redis-trib.rb:1279:in `fix_cluster_cmd'
        from /Redis/RedisHome/bin/redis-trib.rb:1905:in `<main>'
```