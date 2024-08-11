## CR: Custom Resource
- built-in 리소스이외의, 사용자가 정의한 리소스
- built-in 리소스에는 pod, replica, deployment, service 등

## CRD: Custom Resource Definiton
- 커스텀 리소스에 대한 정의

## Controller
- 리소스를 모니터랑히고, 이상적인 상태와 실제 상태를 비교해서 필요한 액션을 수행한다.
- Operator와 거의 비슷한 용어로 사용된다.
- 예를 들어, replica라고 한다면, 
    1. replica 관련 리소스를 꾸준히 관측한다.
    2. replicas가 1에서 3으로 변화한다면? 
        - 이 경우, 이상적인 상태가 1에서 3이 된 것이다.
    3. pod의 수를 2개 더 늘린다.

## Operator 패턴에서 API와 Controller는?
- 