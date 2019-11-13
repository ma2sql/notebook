# fix

## fix_open_slot


## fix_slots_coverage
**fix_slots_coverage** 메서드가 실행되기 위해서는 먼저, **check_slots_coverage** 메서드로부터 실행되는 슬롯 커버리지 체크가 실패해야한다. 슬롯 커버리지란, 말 그대로 레디스 클러스터의 모든 슬롯 16384개가 각각이 하나씩의 노드에 속해야한다는 것이다. 그리고 슬롯 커러리지 체크에 실패했다는 것은 어떤 노드에도 속하지 못한 슬롯이 존재하는 상태라는 것이다.

**fix_slots_coverage** 메서드는 우선 커버되고 있지 않은 슬롯 리스트(**not_covered**)를 작성한다. 그 다음 이 리스트를 순회하며 실제 슬롯이 할당되지 않았지만 이 슬롯의 키를 가진 노드가 있는지를 확인한다. 그리고 아래와 같은 3가지 기준으로 **not_covered**내의 슬롯을 분류한다.

1. **none**: 키를 소유하고 있는 노드가 없는 경우
2. **single**: 키를 소유하고 있는 노드가 하나만 있는 경우
3. **multi**: 키를 소유하고 있는 노드가 두 개 이상인 경우

*참고: 키의 존재 여부를 확인은 `CLUSTER GETKEYSINSLOT` 커맨드가 사용된다.*

**not_covered**의 순회와 슬롯에 대한 분류가 끝나면, 분류별로 각각 다른 방식으로 슬롯 커버리지를 만족하도록 수정을 시도한다.

### 1. none
이 슬롯에 대한 키를 그 어떤 노드도 소유하고 있지 않은 상태이다. 어떠한 노드도 이 슬롯에 대한 키를 소유하고 있지 않기 때문에, 어떠한 마스터에 슬롯이 새롭게 할당되더라도 문제가 되지 않는다. 따라서, **none** 리스트를 순회하며, 각각의 슬롯마다 랜덤하게 마스터를 선택하여 슬롯을 할당하도록 한다. (`CLUSTER ADDSLOTS`)

*다만, 이 부분에서 버그라고 볼 수 있는 것이 존재한다. 랜덤하게 마스터를 선택하는 과정에서 슬레이브 노드 또한 선택의 대상이 되어버린다는 것이다. 실제 코드를 살펴보면, @nodes라는 멤버 변수를 순회하면서 별도로 slave노드를 구분하지 않고 sample(Array#sample(): sample() is a Array class method which returns a random element or n random elements from the array.) 메서드를 호출하는 것이다. 슬레이브 노드에 대해서는 `CLUSTER ADDSLOTS`를 실행할 수 없기 때문에 에러가 발생하며 redis-trib의 실행은 중지된다.*

```ruby
if none.length > 0
    xputs "The folowing uncovered slots have no keys across the cluster:"
    xputs none.keys.join(",")
    yes_or_die "Fix these slots by covering with a random node?"
    none.each{|slot,nodes|
        node = @nodes.sample
        xputs ">>> Covering slot #{slot} with #{node}"
        node.r.cluster("addslots",slot)
    }
end
```

그리고 주의할 것이 하나 있는데, **fail**상태의 마스터 노드가 존재하는 상황에서의 슬롯 커버리지 수정시에는 먼저 **fail**상태의 마스터 노드를 삭제해주어야 한다는 것이다.

예를 들어, 마스터 A는 임의의 슬롯 10개를 보유하고 있고, 이 마스터의 슬레이브 노드는 없다고 가정하자. 서버가 다운되거나 하는 등의 이유로 A노드가 **fail**이 되어버렸다고 할 때, 슬롯 커버리지 체크를 하면 실패 하게 되고, A노드의 슬롯들은 **none** 상태로 분류된다. 이 때, **none**에 대해서 수정을 시도하면 실패하게 되는데, 클러스터 내의 **none** 슬롯의 주인은  아직 A노드인 상태로, `CLUSTER ADDSLOTS`을 통해 다른 노드르 슬롯을 할당하는 것이 불가능하기 때문이다.
```
redis.exceptions.ResponseError: Slot 10923 is already busy
```
따라서, 전체 노드에 대해 `CLUSTER FORGET` 명령으로 **fail** 상태의 노드를 삭제한 다음, 다시 한 번 수정을 시도할 필요가 있다.


### 2. `single`
**not_covered** 슬롯에 대한 키를 하나의 노드만 가지고 있는 상태로, 이 경우에는 키를 소유하고 있는 노드로 슬롯을 할당하도록 하며, `CLUSTER ADDSLOTS` 커맨드만 사용된다.


### 3. `multi`
**not_covered** 슬롯에 대한 키를 두 개 이상의 노드가 가지고 있는 경우라면. 더 많은 수의 키를 보유한 노드를 주인으로 선정하고, 나머지 노드로부터 해당 슬롯의 키를 전달받는다.

어떤 노드가 가장 많은 키를 가지고 있는지는 `CLUSTER COUNTKEYSINSLOT` 커맨드로 확인한다. 이렇게 선정이 되는 주인 노드는 **target**이 되고, 나머지 노드는 **source**가 된다. 먼저, **target**에 대해서 `CLUSTER ADDSLOTS`와 `CLUSTER SETSLOT STABLE` 명령을 실행하여 슬롯을 할당하고 상태를 정리한다. 그리고 본격적으로 **source**로부터 **target**으로 키를 옮기는 작업을 **move_slot** 메서드를 통해 진행된다. 이 때, 중요한 사전 작업으로는 **source** 노드의 슬롯에 대해 `IMPORTING` 상태로 설정하는 것인데, 만약 이러한 설정이 없는 상태에서 **source**에`MIGRATE` 커맨드가 실행되면, 리다이렉션 에러가 발생할 것이기 때문이다. 그렇기 때문에 키를 전달받는 입장이 아니더라도 `IMPORTING` 상태로 설정하는 것이다. (Set the source node in 'importing' state (even if we will actually migrate keys away) in order to avoid receiving redirections for MIGRATE.) 그리고 나서 fix, cold 옵션과 함께 **move_slot** 메서드를 실행하는데, 여기서 cold는 **move_slot**메서드 내부 에서 별도로 실행되는 `IMPORTING`/`MIGRATING` 설정을 무시하는 옵션이며, fix는 옮기려는 키가 **target**노드에 이미 존재하는 경우에는 `MIGRATE` 커맨드를 `REPLACE` 옵션과 함께 재실행되도록 해주는 옵션이다.

> move_slot의 fix 옵션에 대해서는 조금 의문이 든다. **source**로부터 **target**으로 키를 옮길 때, replace를 함께 사용해버리고, 만약 서로 동일한 키에 대해 다른 값이 저장되어 있다고 한다면? 어느 쪽이 맞는지 알기 어려운 상태이긴 한데, **target**을 주인 노드로 설정한 상태에서, **source**노드 기준으로 값을 덮어 쓰는 것이 과연 맞는 것일까? 물론, fix 옵션은 fix_open_slots에서도 사용되므로 그 메서드의 목적에는 부합할지도 모르겠지만 말이다.





