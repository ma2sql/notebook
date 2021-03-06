### MOVED Redirection
- 레디스 클러스터는 기본적으로 슬레이브를 포함한 전 노드가 명령을 받을 수 있다.
- 자신이 가진 슬롯에 해당하는 키라면 직접 처리하고, 그게 아니라면 키가 해당하는 슬롯을 가진 노드로 명령의 처리를 위임한다.
- 이 때, 발생하는 것이 MOVED error이다.
```
GET x
-MOVED 3999 127.0.0.1:6381
```
- 에러에는 Key가 속한 해시 슬롯과 이 슬롯을 가진 노드의 IP:PORT 정보가 포함된다.
- 클라이언트는 이 정보를 이용해서 지정된 노드로 다시 접속해서 명령을 실행할 수 있다.

### ASK Redirection
- 마이그레이션 중인 슬롯의 특정 키에 대한 리다이렉션 처리
- 노드 A가 가진 특정 슬롯 1을 노드 B로 옮긴다고 할 때,
- 노드 A에서의 슬롯 1은 MIGRATING 상태가 되고, 슬롯 내의 키를 하나씩 노드 B로 옮기게 된다.
  - *이 때, 노드 B의 슬롯 1은 IMPORTING 상태*
- 노드 A의 슬롯 1의 키 유/무에 따라 다음과 같은 2가지 상태를 가질 수 있다.
  - 키가 있는 경우
    - 키가 아직 존재하는 경우라면, 정상적으로 명령을 처리한다.
  - 키가 옮겨진 경우
    - ASK 리다이렉션 에러가 발생하고, 이 에러에는 대상 해시 슬롯, 옮겨진 노드 IP:PORT 정보가 표시된다.
```
GET x
-ASK 3999 127.0.0.1:6381
```
- 클라이언트가 ASK 리다이렉션을 수신했을 때,
  1. ASK 리다이렉션이 발생한 쿼리에 대해서만 리다이렉션이 지정된 노드로 명령을 보내고, 후속 쿼리는 계속해서 old node로 명령을 전달한다.
  2. ASKING 명령과 함께 리다이렉트된 쿼리가 실행된다.
  3. migrating 중인 슬롯에 대해서 아직 로컬 클라이언트 테이블을 신규 노드로 변경하진 않는다.
  4. 마이그레이션이 완료된 이후에 old 노드는 MOVED 메시지를 보내고, 신규 노드로 영구 매핑이 가능하다.
  
