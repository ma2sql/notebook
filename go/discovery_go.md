# Discovery Go
본 문서는 `디스커버리 GO` 책을 읽고, 요약한 내용을 정리한다. 

## Chapter 3

### 3.3 맵
선언 형태는 아래와 같다. 
```go
var m map[KeyType]ValueType
```

하지만 이 자체로는 빈 맵으로 취급, 데이터의 변경은 가능하지 않다(불변형 빈 객체인가?). 따라서 아래와 같이 초기화할 필요가 있다.

```go
m := make(map[KeyType]valueType)

// 또는
m := map[KeyType]valueType{}
```

`range`로 반복하는 경우, 키와 값이 나온다. 변수 하나로만 받게 되면 키만 받게 된다.
```go
// 키만 받기
for k := range m {
    // k를 사용
}

// 키 값 받기
for k, v := range m {
    // k, v를 각각 사용
}

// 값만 받기
for _, v := range m {
    // v를 사용
}
```

맵의 요소 삭제
```go
delete(m, key)
```