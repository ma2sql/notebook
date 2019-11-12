# fix

## fix_slots_coverage
**fix_slots_coverage** 메서드가 실행되기 위해서는 먼저, **check_slots_coverage** 메서드로부터 실행되는 슬롯 커버리지 체크가 실패해야한다. 슬롯 커버리지란, 말 그대로 레디스 클러스터의 모든 슬롯 16384개가 각각이 하나씩의 노드에 속해야한다는 것이다. 그리고 슬롯 커러리지 체크에 실패했다는 것은 어떤 노드에도 속하지 못한 슬롯이 존재하는 상태라는 것이다.

**fix_slots_coverage** 메서드는 우선 커버되고 있지 않은 슬롯 리스트(**not_covered**)를 작성한다. 그 다음 이 리스트를 순회하며 실제 슬롯이 할당되지 않았지만 이 슬롯의 키를 가진 노드가 있는지를 확인한다. 그리고 아래와 같은 3가지 기준으로 **not_covered**내의 슬롯을 분류한다.

1. **none**: 키를 소유하고 있는 노드가 없는 경우
2. **single**: 키를 소유하고 있는 노드가 하나만 있는 경우
3. **multi**: 키를 소유하고 있는 노드가 두 개 이상인 경우

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
이 슬롯에 대한 데이터를 하나의 노드만 소유하고 있지 않은 상태. 이 경우에는 소유한 노드가 슬롯을 소유하도록 해주면 된다.

이것은 어떠한 상황에서 발생하게 될 것인가? 클러스터를 확장하는 경우, IMPORTING/MIGRATING 상태를 정리하려는 상황에서 MIGRATING 노드가 페일오버된다. slave가 마스터가 되면서 MIGRATING 상태가 해제된다. 그리고 IMPORTING 상태의 노드 역시 `CLUSTER SETSLOT` 명령을 받지 못한다면?
IMPORTING 상태로 남이있게 될 것이다.

다만.. `IMPORTING` 상태에 대해서는 **fix_open_slots** 에서 먼저 정리될 수 있을 듯 한데.. 음


### 3. `multi`
이 슬롯에 대한 데이터를 두 개 이상의 노드가 소유하고 있는 경우라면. 더 많은 수의 키 (`CLUSTER COUNTKEYSINSLOT`) 를 보유한 노드를 주인으로 두고, 나머지 노드에서는 해당 슬롯의 데이터를 주인 노드로 옮긴다.

먼저, 소스 노드(주인이 아닌 노드)에 `CLUSTER SETSLOT IMPORTING`를 실행한다. 실제로는 마이그레이션하는 소스 노드이지만, `IMPORTING`을 설정하는 이유는, 바로 이 노드로 `MIGRATE` 커맨드가 실행되어야하기 때문이다. 만약, IMPORTING 상태로 만들지 않는다면, MIGRATE 커맨드는 리다이렉션이 되어버리고 말 것이다.

그리고 나서, fix, cold 옵션을 부여하여 source로부터 target(주인)으로 move_slot을 실행시킨다. 여기서 cold 옵션의 효과는 reshading/rebalancing 등에서 move_slot을 사용할 때 처럼 target을 IMPORTING, source를 MIGRATING으로 두지 않기 위함이다. 이미 ADDSLOT으로 주인 노드를 할당해둔 상태이고, MIGRATING 모드는 보통 주인 노드에서 실행되는 것으로 fix하기 위한 목적과는 맞지 않기 때문이다.







