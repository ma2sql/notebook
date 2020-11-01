## fix

### fix open slot

#### 1. owners, owner 후보자 선택
- 후보자 선택의 조건
  - `CLUSTER NODES` 출력 결과로부터 슬롯의 보유 사실을 알 수 있을 때
  - 슬롯을 보유하고 있지는 않지만, `CLUSTER COUNTKEYSINSLOT` 명령을 통해서 해당 슬롯에 대한 키를 가지고 있는 사실을 알 수 있을때
- 주의: migrating 상태는 owner가 아닐 수 있다!
  - 마이그레이션이 완료되고, importing만 정리되고, migrating 상태는 미쳐 정리되지 못했을 때
    - importing노드는 새롭게 epoch를 받기 때문에, migrating보다 아마도 더 높은 epoch를 가질 것
    - 따라서, migrating 상태는 유지되지만 epoch차이로 해당 슬롯에 대한 onwer가 아니게 되는 상태가 생길 수 있다.


#### 2. MIGRATING/IMPORTING 상태를 구분
- MIGRATING
  - `CLUSTER NODES` 출력 결과로부터 슬롯이 **MIGRATING** 상태를 알 수 있을 때
- IMPORTING
  - `CLUSTER NODES` 출력 결과로부터 슬롯이 **IMPORTING** 상태를 알 수 있을 때
  - **IMPORTING** 상태는 아니지만, `CLUSTER COUNTKEYSINSLOT` 명령을 통해서 해당 슬롯에 대한 키를 가지고 있는 사실을 알 수 있을때

#### 3. owner 후보자들로부터 owner를 선출하기
1. owners에 하나의 노드만 있을 때,
    - 그 하나의 노드를 owner로 선출
2. owners에 2개 이상의 노드가 있을 때,
    - 각각의 후보자들을 대상으로 `CLUSTER COUNTKEYSINSLOT`를 수행하고, 키를 가장 많이 가진 노드를 owner로 선출
    - 여기서 선출된 owner에 대해서는 slot을 명시적으로 할당해준다.
      - `CLUSTER SETSLOT __slot__ STABLE`
      - `CLUSTER DELSLOTS __slot__`
      - `CLUSTER ADDSLOTS __slot__`
      - `CLUSTER SETSLOT __slot__ STABLE`
      - `CLUSTER BUMPEPOCH`
    - MIGRATING/IMPORTING 상태라면, 이 단계에서 상태가 정리된다. (clear)
    - 그리고 2번에서 분류한 MIGRATING/IMPORTING 각가의 리스트로부터 owner로 선출된 노드를 제거한다.


#### 4. owner 후보자들이 다수일 때
- owner인 노드를 제외하고, 나머지는 모두 IMPORTING 상태로 설정한다.
  - `CLUSTER SETSLOT __slot__ NODE __owner_id__`
  - `CLUSTER SETSLOT __slot__ IMPORTING __owner_id__`
- owner이외의 노드를 IMPORTING 리스트로 추가한다. 
  - 만약, 이미 MIGRATING 리스트에 속한다면, 그 리스트에서도 제외시킨다.


#### 5. FIX: case1: migrating과 importing이 각각 하나씩만 존재할 때
- importing, migrating 노드 각각 키를 하나도 가지고 있지 않을 때
- 또는, importing 노드에서는 키를 가지고 있지 않을 때
  - importing노드가 키를 가지고 있으면, onwer의 후보자가 되며
  - 후보자가 2이상일 때에는 owner 선출 과정을 거치면서, 
    - 결과적으로 migrating 상태는 없어지고, importing 상태만 남는다.
- 이 경우에는 migrating에서 importing으로 move slot을 실행한다.


#### 5. FIX: case2: migrating는 0, importing은 하나 이상일 때
- importing 노드를 순회하면서, owner 노드로 move_slot을 실행한다.
- owner노드로 모든 키를 다 옮겼다면, `CLUSTER SETSLOT __slot__ STABLE`로 importing 상태를 정리한다.
- 모든 importing 노드로부터 모든 키를 owner로 다 옮겼다면, 전 노드를 순회하면서 명시적으로 owner가 slot의 주인임을 선언한다.
  - `CLUSTER SETSLOT __slot__ NODE __owner_id__`


#### 5. FIX: case3: migaring은 하나, importing은 2개 이상일 때
- importing이 여러개가 인식이 되었지만, 키를 가지고 있지 않아서, owner후보자가 되지 못한 경우
- migrating이 곧 owner
1. migrating이 옮기려고 했던 노드의 target_id를 찾는다.
2. importing 노드를 순회하면서, target_id와 같은 노드를 찾아, dst 노드로 지정한다.
3. dst를 발견한 경우에는, 
   - migrating에서 dst로 키를 모두 옮긴다.
   - 나머지 importing 노드는 모두 슬롯 상태를 정리한다.
     - `CLUSTER SETSLOT __slot__ STABLE`
4. dst를 발견하지 못한 경우에는,
   - migrating 노드의 상태를 정리한다./
     - `CLUSTER SETSLOT __slot__ STABLE`
   - 모든 importing 노드를 순회하면서 상태를 정리한다.
     - `CLUSTER SETSLOT __slot__ STABLE`


#### 5. FIX: case4: migarting은 하나, importing은 존재하지 않을 때
- 아마도 move_slot을 극초반 또는 극후반에 작업이 멈춘 경우
  - migrating이 owner이면, 
    - migrating 이외에 키를 가진 노드가 없었다는 것
    - migrating 노드는 키를 갖고 있을 수 있다.
  - migrating이 owner가 아니라면,
    - 다른 더 높은 epoch를 가진 노드가 이미 주인
    - migrating 노드는 더 이상 cluster 상에서 owner가 아닐 때
      - 즉, 이러한 경우에 migrating은 owner로 판명되지 않을 수 있다.
    - 이 경우, migrating은 키를 가지고 있지 않다고 하자
  - migrating이 owner가 아닐 때
- migrating 노드를 단순히 정리햐는 것으로 종료
  - `CLUSTER SETSLOT __slot__ STABLE`
- migrating 노드가 키를 가지고 있는데, owner가 아니라면 fix 실패
  - `CLUSTER GETKEYSINSLOT __slot__`
  - 아마 키를 가지고 있었다면, 이미 owner 후보자가 되었을 것이고, migrating은 정리가 되었을 것이다.
