## redis-trib.rb

### add-node
- --slave 옵션이 추가되었을 때,
  - master-id 옵션이 같이 지정되지 않는다면, replica의 수가 가장 적은 마스터들 중 하나를 선택한다.
    - 딱히 랜덤 처리를 하지는 않는데, 동률에 대한 정렬 순서를 보장하지는 않는다.
      - 정렬 순서는 load_cluster_info_from_node 에 영향을 받을 수 있다.
      - 다만, existing_host:existing_port에 지정된 노드의 정보는 보통 nodes 정보의 맨 앞에 위치하므로,
      - replicas가 모두 동률이라면, existing_host:existing_port가 master가 될 확률이 매우 높다.
  - master-id 옵션이 같이 지정된다면, 지정된 master-id에 대해서 replication을 연결한다.

  
 
### fix
code의 실행 순서
- fix_cluster_cmd
  - load_cluster_info_from_node
    - 실제 이 지점에서 각 슬롯별 정보가 취득된다.
  - migrating/importing 상태에 따라, 각각의 딕셔너리? 객체에 저장된다.
  - :migrating / :importing 으로 접근이 가능하다.
- check_cluster
  - show_nodes
  - check_config_consistency
    - is_config_consistent
      - 클러스터마다 cluster nodes 명령을 수행한 다음, 각각의 결과가 일치하는지를 확인
  - check_open_slots
    - :migrating, :importing 상태의 슬롯을 open_slots로 표현
    - 각각의 open_slots에 대해서 fix_open_slot 메서드를 실행
    - fix_open_slot
      - get_slot_owners
        - 슬롯의 주인을 확인
      - importing/migrating 각각으 분류
        - 주인이 없으면(no owners) importing으로 분류
      - 주인이 없는 경우,
        - 전체 노드를 뒤져, 동일 슬롯에 대해 키의 개수가 가장 많은 노드를 선택하여, owner로 만듦
        - owner 작성 이후, 다음 두 명령을 실행
          - cluster setslot {slot} stable
          - cluster addslots {slot}
      - 주인이 2 이상인 경우
        - 슬롯의 키가 더 많은 쪽을 복구 대상으로 선택
        - 주인이 아닌쪽
        
  - check_slots_coverage


### client-output-buffer-limit
- client-output-buffer-limit은 기본적으로 클라이언트의 요청에 대한 응답을 비동기적으로 수행하기 위한 것으로 보인다.
- addReply 라는 함수가 지속적으로 호출되는데, 처리 결과를 즉시 클라이언트에게 return하는 것이 아니라, output 버퍼에 담아둔다.
  - 아마도 비동기적인 처리 흐름을 가져가기 위한 것으로 보인다.
- 특정한 타이밍에 일괄적으로 보내는 것으로 보인다.
- Replication 시점에도 이는 마찬가지인데,
  - Replication이 시작하면 BGSAVE에 의해 RDB가 수행된다.
    - *RDB의 slave 전송 시점에 output buffer를 사용하는지는 아직 알 수가 없다.*
    - 이 시점부터의 write 요청은 아마 client(slave)의 output buffer에 저장되기 시작한다.
    - BGSAVE가 완료되고, 슬레이브에 이것이 로딩되기까지 output buffer에 저장되고, 전송된다.

### backlog
- 아마도 이것은 replication연결 도중, slave와의 단절이 있었을 때,
- 데이터를 저장해두는 곳