# Redis RDB File Format

Redis의 *.rdb 파일은 인 메모리(in-memory) 저장소의 바이너리 표현이다. 바이너리 파일은 Redis의 상태를 완벽히 복원하기에 충분하다.

rdb파일 포맷은 빠른 읽기와 쓰기를 위해 최적화되어 있다. LZF가 가능한 곳(환경)에서는 파일 사이즈를 줄이기 위해 압축이 사용된다. 일반적으로, 오브젝트는 길이 정보가 앞쪽에 위치해서, 오브젝트를 읽기 전에 얼마만큼의 메모리를 할당해야할지를 정확히 알 수 있다.

빠른 읽기/쓰기를 위해 최적화하는 것은 디스크상(on-disk)의 포맷이 가능한한 인 메모리(in-memory)표현과 가까워야 한다는 것을 의미한다. 이것은 rdb 파일이 취하는 접근법이다. 따라서, Redis 데이터 구조의 인 메모리(in-memory)표현에 대한 어느 정도의 이해가 없이는 rdb파일을 파싱할 수 없다.

## High Level Algorithm to parse RDB

At a high level, the RDB file has the following structure
고수준에서, RDB 파일은 다음과 같은 구조를 가진다.

```
----------------------------# RDB는 바이너리 포맷이다. 파일내에 새로운 행(new line)이나 공백은 없다.
52 45 44 49 53              # 매직 스트링(Magic String)은 "REDIS"이다.
30 30 30 37                 # 4자리의 ASCCII RDB 버전 숫자. 여기서는 version = "0007" = 7
----------------------------
FE 00                       # FE = 데이터베이스 선택자를 표시하는 코드. db number == 00
----------------------------# 키-값 쌍이 시작됨
FD $unsigned int            # FD는 "초 단위의 만료시간을 표기한다". 그 후, 만료 시간은 부호없는 4byte의 정수로 읽힌다.
$value-type                 # 1 byte 플래그는 값(value)의 타입을 표시한다. - set, map, sorted set 등등
$string-encoded-key         # 레디스 문자열(string)으로 인코딩된 키(key)
$encoded-value              # 값(value). 값의 타입($value-type)에 따라 다르다.
----------------------------
FC $unsigned long           # FC는 밀리초(ms)의 만료 시간을 나타낸다. 그 후, 만료 시간은 8byte의 부호없는 long 타입으로 읽혀진다.
$value-type                 # 값(value)의 타입을 나타내는 1 byte의 플래그. set, map, sorted set, etc..
$string-encoded-key         # 레디스 문자열 (redis string)으로 인코딩된 키 (key)
$encoded-value              # $value-type에 따라 인코딩된 값 (value)
----------------------------
$value-type                 # 이 키-값(key-value) 쌍은 만료 시간을 가지지 않는다, $value_type이 FD, FC, FE, FF가 아닌 것을 보장한다.
$string-encoded-key
$encoded-value
----------------------------
FE $length-encoding         # 이전 db가 끝나고, 다음 db가 시작된다. 데이터베이스 번호는 인코딩 길이 (length-encodig)를 사용해서 읽어진다.
----------------------------
...                         # 이 데이터베이스에 대한 키-값 쌍들, 그리고 추가적인 데이터베이스
                            
FF                          ## RDB파일의 끝에 대한 지시자
8 byte checksum             ## 전체 파일의 CRC 64 체크섬(checksum)
```

### Magic Number

파일은 매직 문자열 "REDIS"와 함께 시작된다. 이것은 우리가 rdb 파일을 다루고 있음을 알기 위한, 빠른 새너티 체크(sanity check)이다.

`52 45 44 49 53  # "REDIS"`

### RDB Version Number

다음 4byte는 rdb 포맷의 버전 번호를 저장한다. 4byte는 아스키 문자열로 해석된 다음, 정수형으로 변환되는데, 이때 문자열과 정수형 컨버전을 이용한다.

`00 00 00 03 # Version = 3`

### Database Selector

레디스 인스턴스는 여러 개의 데이터베이스를 보유할 수 있다.

단일 byte `0xFE`는 데이터베이스 선택자(selector)의 시작을 표시한다. 이 byte 다음에, 변수 길이 필드는 데이터베이스 번호를 표시한다. 데이터베이스 번호를 읽는 방법을 이해하려면, 다음 섹션인 "[Length Encoding](#length-encoding)"을 참고하라.

### Key Value Pairs

데이터베이스 선택자 이후, rdb 파일은 키-값 쌍의 연속을 포함한다.

각 키-값 쌍은 4가지 부분으로 나뉜다 -

1. 키 만료시간의 타임스탬프. 선택적으로 포함
2. 값에 대한 타입을 표시하는 1byte의 플래그
3. 레디스 문자열(Redis String)로 인코딩돤 키. "Redis String Encoding"를 참고
4. 값 타입(value type)에 따리 인코딩된 값. "Redis Value Encoding"를 참고

#### Key Expiry Timestamp

이 섹션은 1byte의 플래그로 시작한다. `FD`는 만료 시간이 초 단위로 지정되었다는 것을 나타낸다. `FC`는 만료 시간이 밀리초 단위로 지정되었다는 것을 나타낸다.

만약 시간이 밀리초로 지정된다면, 다음 8byte는 유닉스 타임(unix time)을 표현한다. 이 숫자는 초 또는 밀리초 정밀도의 유닉스 타임스탬프 (unix timestamp)이고, 이 키의 만료 시간을 나타낸다.

이 숫자가 인코딩되는 방법에 관해서는 "Redis Length Encoding" 섹션을 참고하라.

임포트 프로세스동안, 만료된 키는 폐기될 것이다.

#### Value Type

이 1 byte 플래그는 값을 저장하기 위해 사용되는 인코딩을 나타낸다.

1. 0 =  "String Encoding"
2. 1 =  "List Encoding"
3. 2 =  "Set Encoding"
4. 3 =  "Sorted Set Encoding"
5. 4 =  "Hash Encoding"
6. 9 =  "Zipmap Encoding"
7. 10 = "Ziplist Encoding"
8. 11 = "Intset Encoding"
9. 12 = "Sorted Set in Ziplist Encoding"
10. 13 = "Hashmap in Ziplist Encoding" (Introduced in rdb version 4)

#### Key 

키는 단순히 레디스 문자열(Redis string)로 인코딩된다. 키가 인코딩되는 방법에 대해서 알고 싶다면, "[String Encoding](#string-encoding)"를 참고하라.

#### Value

값의 인코딩은 값 타입 플래그에 따라 달라진다.

- 0일 때, 값은 단순한 문자열이다.
- 9, 10, 11, 12 중에 하나일 때, 값은 문자열로 래핑된다. 이 문자열을 읽고 나서, 더 파싱되어야 한다.
- 1, 2, 3, 4 중에 하나일 때, 값은 문자열의 연속(sequence)이다. 이 문자열의 연속은 리스트나, 셋, 정렬된 셋 또는 해시 맵을 구성하기 위해서 사용된다.

## Length Encoding

길이 인코딩(Length encoding)은 스트림 내의 다음 오브젝트의 길이를 저장하는데 사용된다. 길이 인코딩은 가능한 한 더 적은 byte를 사용하도록 설계된 변수 byte 인코딩이다.

이것은 길이 인코딩이 동작하는 방법이다:

1. 스트림으로부터 1byte를 읽어, 최상위(most significant bits) 2비트를 읽는다.
2. `00`으로 시작하면, 그 다음 6비트는 길이를 나타낸다.
3. `01`로 시작하면, 스트림으로부터 추가적인 byte를 읽어야한다. 조합된 14비트로 길이를 나타낸다.
4. `10`으로 시작하면, 나머지 6비트는 버려진다. 스트림으로부터 추가적으로 4byte를 읽고, 이 4byte가 길이(RDB의 버전이 6에서는 빅 엔디안 포맷)를 나타낸다. 
5. `11`로 시작하며느 다음 오브젝트는 특별한 포맷으로 인코딩된다. 나머지 6비트는 이 포맷을 표시한다. 이 인코딩은 일반적으로 숫자를 문자열로 저장하거나, 인코딩된 문자열을 저장하기 위해 사용된다. "[String Encoding](#string-encoding)"을 참고

이 인코딩의 결과로 -

1. 63을 포함하는 숫자까지, 1byte러 저장할 수 있다.
2. 16383을 포함하는 숫자까지, 2byte로 저장할 수 있다.
3. 2^32-1을 포함하는 숫자까지는 5byte로 저장할 수 있다.

## String Encoding

레디스 문자열(Redis Strings)은 바이너리에 안전하다. 이것은 무엇이든 레디스 문자열로 저장할 수 있다는 것을 의미한다. 어떤 특별한 end-of-string 토큰을 가지지 않는다. 레디스 문자열은 byte의 배열로 생각하는 것이 가장 좋다.

레디스에는 세 가지 타입의 문자열이 있다 -

1. 길이 접두사 문자열(Integers as String)
2. 8, 16, 또는 32비트의 정수
3. LZF로 압축된 문자열

#### Length Prefixed String

길이가 접두사 문자열은 매우 간단하다. byte로된 문자열의 길이는 먼저 "길이 인코딩(Length Encoding)"을 이용해서 인코딩된다. 이 이후에, 문자열의 원시 byte(raw bytes)가 저장된다.

#### Integers as String

먼저 "길이 인코딩(Length Encoding)" 섹션, 특히 최상위 2비트가 `11`인 부분을 읽는다. 이 경우, 남은 6비트를 읽는다.
만약 이 6비트의 값이 -

1. 0이면, 8비트의 정수가 이어진다는 것을 의미한다.
2. 1이면, 16비트의 정수가 이어진다는 것을 의미한다.
3. 2이면, 32비트의 정수가 이어진다는 것을 의미한다.

#### Compressed Strings

먼저 "길이 인코딩(Length Encoding)" 섹션, 특히 최상위 2비트가 `11`인 부분을 읽는다. 이 경우, 남은 6비트를 읽는다.
만약 이 6비트의 값이 4라면, 이것은 압축된 문자열이 이어진다는 것을 의미한다.

압축된 문자열은 다음과 같이 읽는다 -

1. 압축된 길이 `clen`을 스트림에서 "길이 인코딩 (Length Encoding)"을 이용해서 읽는다.
2. 압축되지 않은 길이를 스트림에서 "길이 인코딩 (Length Encoding)"을 이용해서 읽는다.
3. 그 다음 `clen` byte를 스트림에서 읽는다.
4. 마지막으로, 이 byte들을 LZF 알고리즘을 이용해서 압축을 해제한다.

## List Encoding

레디스 리스트(redis list)는 문자열의 연속으로 표현된다.

1. 먼저, 리스트 `size`의 크기를 스트림에서 "길이 인코딩 (Length Encoding)"을 이용해서 읽는다.
2. 그 다음, `size` 문자열을 스트림에서 "문자열 인코딩 (String Encoding)"을 이용해서 읽는다.
3. 그런 다음, 이 문자열들을 이용해서 리스트를 재구성한다.

## Set Encoding

셋은 정확히 리스트처럼 인코딩된다.

## Sorted Set Encoding

1. 먼저, 정렬된 셋 `size`의 크기를 스트림에서 "길이 인코딩 (Length Encoding)"을 이용해서 읽는다.
2. TODO

## Hash Encoding

1. 먼저, 해시 `size`의 크기를 스트림에서 "길이 인코딩 (Length Encoding)"을 이용해서 읽는다.
2. 그 다음, `2 * size` 문자열을 스트림에서 "문자열 인코딩 (String Encoding)"을 이용해서 읽는다.
3. 번갈아 나오는 문자열은 키와 값이다.
4. 예를 들어, ` 2 us washington india delhi `는 맵 `{"us" => "washington", "india" => "delhi"}`로 표현된다.

## Zipmap Encoding

NOTE : Zipmap 인코딩은 레디스 2.6부터 사용되지 않는다. 이제, 작은 해시맵은 ziplists를 이용해서 인코딩된다.

zipmap은 문자열로 직렬화된 해시맵이다. 본질적으로, 키-값 쌍은 연속적으로 저장된다. 이 구조에서 키를 찾는 것은 O(N)이다. 이 구조는 키-값 쌍의 수가 적을 때, 딕셔너리 대신 사용된다.

zipmap을 파싱하려면, 우선 문자열을 스트림에서 "문자열 인코딩 (String Encoding)"을 이용해서 읽는다. 이 문자열은 zipmap감싸여져 있다. 문자열의 내용은 zipmap으로 나타난다.

이 문자열 내의 zipmap 구조는 다음과 같다 -

`<zmlen><len>"foo"<len><free>"bar"<len>"hello"<len><free>"world"<zmend>`

1. *zmlen* : 1 byte 길이이다. zipmap의 크기를 가지고 있는 1byte의 길이이다. 만약, 254과 같거나 크다면, 이 값은 사용되지 않는다. 길이를 찾으려면 zipmap 전체를 순회해야한다.
2. *len* : 이어지는 문자열의 길이이다. 그리고 이 문자열은 키 또는 값이 될 수가 있다. 이 길이는 1 byte 또는 5 byte("길이 인코딩 (Length Encoding)"과는 다르다)로 저장된다. 만약, 첫 byte가 0에서 252사이라면, 그것은 zipmap의 길이이다. 만약, 첫 byte가 253이면, 그 다음 4byte를 zipmap의 길이를 나타내는 부호 없는 정수형으로 읽는다. 254에서 255는 이 필드에서 유효하지 않은 값이다.
3. *free* : 이것은 항상 1byte이며, 값(value) 이후의 여유 공간 (free byte)의 수를 나타낸다. 예를 들어, 한 키의 값이 "America"이고, 이것이 "USA"로 업데이트된다면, 4byte의 여유 공간이 사용 가능하게 된다.
4. *zmend* : 항상 255. zipmap의 끝을 나타낸다.


*Worked Example*

`18 02 06 4d 4b 44 31 47 36 01 00 32 05 59 4e 4e 58 4b 04 00 46 37 54 49 ff ..`

1. "문자열 인코딩 (String Encoding)"을 이용한 디코딩으로 시작된다. `18`은 문자열의 길이라는 것을 알 수 있다. 따라서, 우리는 그 다음 24byte를 읽을 것이고, 즉(i.e.) `ff`까지이다.
2. 이제, 우리는 "Zipmap Encoding"을 이용해서 `02 06... `으로 시작하는 문자열을 분석할 것이다.
3. `02`는 해시맵내의 엔트리 수이다.
4. `06`은 다음 문자열의 길이이다. 254보다 작기 때문에, 추가적인 byte를 읽지 않아도 된다.
5. 다음 6byte, 즉`4d 4b 44 31 47 36` 를 읽고, 키(key) "MKD1G6"을 얻는다.
6. `01`은 다음 문자열인 값(value)의 길이이다.
7. `00`은 여유(free) byte의 길이이다.
8. 다음 1byte, `0x32`를 읽는다. 그래서 값 "2"를 얻는다.
9. 이 경우, 여유 byte는 0이고, 그래서 우리는 어떤것도 생략하지 않는다.
10. `05`는 다음 문자열의 길이이고, 이 경우에는 키(key)이다.
11. 다음 5byte `59 4e 4e 58 4b`를 읽고, 키(key) "YNNXK"를 언든다.
12. `04` is the length of the next string, which is a value
12. `04`는 다음 문자열인 값(value)의 길이이다.
13. `00`은 값(value) 이후의 여유(free) byte의 수이다.
14. 그 다음 4byte, 즉 `46 37 54 49`를 읽고, 값 "F7TI"를 얻는다.
15. 마지막으로, `FF`를 만나게 되고, 이것은 zipmap의 끝을 의미한다.
16. 그러므로, 이 zipmap은 해시 `{"MKD1G6" => "2", "YNNXK" => "F7TI"}`를 표현한다.

## Ziplist Encoding

ziplist는 문자열로 직렬화된 리스트이다. 본질적으로, 리스트의 엘리먼트들은 양방향으로 리스트를 효율적으로 순회할 수 있도록 플래그와 오프셋과 함께 연속적으로 저장된다. 

ziplist를 파싱하려면, 우선 스트림에서 문자열을 "문자열 인코딩 (String Encoding)"을 이용해서 읽는다. 이 문자열은 ziplist로 감싸여져 있다. 문자열의 내용은 ziplist로 나타난다.

이 문자열 내 ziplist의 구조는 다음과 같다 -

`<zlbytes><zltail><zllen><entry><entry><zlend>`

1. *zlbytes* : 이것은 4byte의 부호없는 정수형으로 ziplist의 전체 크기를 byte로 표시한다. 4byte는 리틀 엔디안(little endian) 포맷이다. (최하위 비트가 첫 위치로 온다.)
2. *zltail* : 이것은 4byte의 부호없는 정수형으로 리틀 엔디안 포맷이다. ziplist 내의 끝부분, 즉 마지막 엔트리에 대한 오프셋을 나타낸다.
3. *zllen* : 이것은 2byte의 부호없는 정수형으로 리틀 엔디안 포맷이다. ziplist내의 엔트리 개수를 나타낸다.
4. *entry* : ziplist내의 엔트리를 나타낸다. 자세한 것은 아래를 참고
5. *zlend* : 이것은 항상 `255`이다. ziplist의 끝을 나타낸다.


ziplist내의 각 엔트리는 다음과 같은 포맷을 가진다 :

`<length-prev-entry><special-flag><raw-bytes-of-entry>`

*length-prev-entry* : 이 필드는 이전 엔트리의 길이를 저장하는데, 만약 첫 번째 엔트리라면 0을 저장한다. 이것은 리스트를 역방향으로 쉽게 탐색할 수 있게 해준다. 이 길이는 1byte 또는 5byte로 저장된다. 만약 첫 byte가 253보다 같거나 작으면, 길이로 간주된다. 첫 byte가 254라면, 그 다음 4byte가 길이를 저장히기 위해 사용된다. 4byte는 부호없는 정수형으로 해셕된다.

*Special flag* : 이 플래그는 엔트리가 문자열인지 정수형인지를 표시한다. 또한, 문자열의 길이나 정수형의 크기를 표시하기도 한다.

이 플래그의 다양한 인코딩은 다음과 같다 : 

1. |00pppppp| - 1 byte : 길이가 63 byte(6 비트) 이하인 문자열 값.
2. |01pppppp|qqqqqqqq| - 2 bytes : 길이가 16383 byte(14 비트) 이하인 문자열 값.
3. |10______|qqqqqqqq|rrrrrrrr|ssssssss|tttttttt| - 5 bytes : 길이가 16384 byte(14 비트) 이상인 문자열 값.
4. |1100____| - 다음 2byte를 16비트의 부호있는 정수로 읽는다.
5. |1101____| - 다음 4byte를 32비트의 부호있는 정수로 읽는다.
6. |1110____| - 다음 8byte를 64비트의 부호있는 정수로 읽는다. 
7. |11110000| - 다음 3byte를 24비트의 부호있는 정수로 읽는다.
8. |11111110| - 다음 1byte를 8비트의 부호있는 정수로 읽는다.
9. |1111xxxx| - (with xxxx between 0000 and 1101) 4비트에 가까운 정수. 0에서 12사이의 부호없는 정수. 인코딩된 값은 실제 1에서 13사이지만, 0000과 1111은 사용될 수 없기 때문에, 올바른 값을 얻기 위해서는 인코딩된 4비트 값에서 1을 빼야한다.

*Raw Bytes* : 스페셜 플래그 (special flag) 이후, 엔트리의 원시 byte(raw bytes)가 이어진다. byte의 수는 이전 스페셜 플래그의 일부로서 결정된다. 

*Worked Example 1*

```
23 23 00 00 00 1e 00 00 00 04 00 00 e0 ff ff ff ff ff ff ff 7f 0a d0 ff ff 00 00 06 c0 fc 3f 04 c0 3f 00 ff ... 
  |           |           |     |                             |                 |           |           |       

```

1. "문자열 인코딩 (String Encoding)"을 이용해서 디코딩을 시작한다. `23`은 문자열의 길이이므로, 다음 35byte인 `ff`까지 읽을 것이다.
2. 이제, "Ziplist encoding"을 이용해서 `23 00 00 ...`으로 시작하는 문자열을 파싱할 것이다.
3. 처음 4byte `23 00 00 00`는 이 ziplist의 전체 길이를 byte로 표현한다. 이것은 리틀 엔디안 포맷임을 주의하라.
4. 다음 4byte `1e 00 00 00`는 마지막(tail) 엔트리의 오프셋을 나타낸다. `1e` = 30 이고, 이것은 0을 기준으로한 오프셋이다. 0번째 위치는 `23`, 첫번째 위치는 `00`, 그리고 기타 등등. 그렇게 `04 c0 3f 00 ..`로 시작하는 마지막 엔트리까지 이어진다.
5. 다음 2byte `04 00`는 리스트 내의 엔트리의 개수를 나타낸다.
6. 이제부터, 엔트리를 읽기 시작한다.
7. `00`은 이전 엔트리의 길이를 나타낸다. 0은 이것이 첫 엔트리라는 것을 나타낸다.
8. `e0`은 스페셜 플래그이다. 이것은 비트의 패턴이 `1110____`로 시작하기 때문에, 다음 8byte를 정수로 읽는다. 이것은 리스트의 첫 번째 엔트리이다.
9. 이제 두 번째 엔트리를 시작한다.
10. `0a`는 이전 엔트리의 길이이다. 이전 10byte는 1byte(로 표현). 길이(length)를 나타내는 (1)byte + 스페셜 플래그 1byte + 정수 8byte.
11. `d0`은 스페셜 플래그이다. 이것은 비트의 패턴이 `1101____`로 시작하기 때문에, 다음 4byte를 정수로 읽는다. 이것은 리스트의 두 번째 엔트리이다.
12. 우리는 이제 세 번째 엔트리를 시작한다.
13. `06`은 이전 엔트리의 길이이다. 이전 6byte는 1byte(로 표현). 길이(length)를 나타내는 (1)byte + 스페셜 플래그 1byte + 정수 4byte.
14. `c0`은 스패셜 플래그이다. 이것은 비트의 패턴이 `1100____`로 시작하기 때문에, 다음 2byte를 정수로 읽는다. 이것은 리스트의 세 번째 엔트리이다.
15. 우리는 이제 마지막 엔트리를 시작한다.
16. `04`는 이전 엔트리의 길이이다.
17. `c0`은 2byte의 숫자를 나타낸다.
18. 다음 2byte를 읽으면, 4번째 엔트리가 나온다.
19. 마침내, `ff`를 만나며, 이것은 ziplist내의 모든 엘리먼트를 소비했다는 것을 말해준다.
20. 그러므로, 이 ziplist는 값 `[0x7fffffffffffffff, 65535, 16380, 63]`을 저장한다.

## Intset Encoding

Intset은 정수의 이진 탐색 트리이다. 이 이진 트리는 정수의 배열로 구현된다. 집합(set)의 모든 엘리먼트가 정수일 때, Intset은 사용된다. Intset은 최대 64비트의 정수까지 지원한다. 최적화로써, 만약 정수가 작은 바이트로 표현될 수 있다면, 정수의 배열은 16 또는 32비트로 구성될 수 있다. 새로운 엘리먼트가 입력될 때의 구현은 필요하다면 업그레이드하도록 관리한다.

Intset은 이진 탐색 트리이기 때문에, 이 집합내의 숫자는 항상 정렬된다.

Intset은 집합(set)의 외부(external) 인터페이스를 가지고 있다.

Intset을 파싱하려면, 먼저 스트림에서 "문자열 인코딩 (String Encoding)"을 이용해서 문자열을 읽는다. 이 문자열은 Intset으로 감싸여져 있다. 이 문자열의 내용은 Intset으로 표현된다.

이 문자열내에서, Intset은 매우 단순한 레이아웃을 가진다 :

`<encoding><length-of-contents><contents>`

1. *encoding* : 이것은 32비트의 부호없는 정수이다. 가능한 값은 2, 4, 또는 8이다. 컨텐츠에 저장되는 각각의 정수의 크기를 바이트 단위로 나타낸다. 그리고 그렇다면, 이것은 낭비가 되는데, 동일한 정보를 2비트 내에서 저장할 수 있기 때문이다.
2. *length-of-contents* : 이것은 32비트의 부호없는 정수이고, 컨텐츠 배열의 길이를 나타낸다.
3. *contents* : 이것은 $length-of-contents 바이트의 배열이다. 정수의 이진 트리를 포함한다.

*Example*

`14 04 00 00 00 03 00 00 00 fc ff 00 00 fd ff 00 00 fe ff 00 00 ...`

1. "문자열 인코딩 (String Encoding)"을 이용해서 디코딩을 시작한다. `14`는 문자열의 길이이므로, 다음 20byte인 `00`까지 읽을 것이다.
2. 이제, `04 00 00 ... `로 시작하는 문자열을 해석하기 시작한다.
3. 첫 4byte `04 00 00 00`는 인코딩이다. 이것은 4로 평가되기 때문에, 4바이트의 정수로 다루어야한다는 것을 알 수 있다.
4. 다음 4byte `03 00 00 00`는 컨텐츠의 길이이다. 그러므로, 각각 4바이트의 long타입인 정수 3개를 다루어야한다는 것을 알 수 있다.
5. 이제부터, 4바이트의 그룹을 읽고, 부호가 없는 정수로 변환한다.
6. 그러므로, 이 intset은 `0x0000FFFC, 0x0000FFFD, 0x0000FFFE`처럼 보인다. 정수는 리틀 엔디안 포맷. 즉, 최하위 비트가 첫번째로 오는 것에 주의해야한다.

## Sorted Set as Ziplist Encoding

ziplist로 인코딩된 정렬된 셋(sorted set)은 위에서 설명한 Ziplist같이 저장된다. 정렬된 셋내의 각 엘리먼트는 ziplist의 점수(score)로 이어진다.

*Example*

`['Manchester City', 1, 'Manchester United', 2, 'Tottenham', 3]`

보다시피, 점수(score)는 각 엘리먼트에 뒤따른다.

## Hashmap in Ziplist Encoding

여기에서, 해시맵의 `키=값`쌍은 ziplist내에 연속적인 엔트리로 저장된다.

Note : This was introduced in rdb version 4. This deprecates zipmap encoding that was used in earlier versions.

*Example*

`{"us" => "washington", "india" => "delhi"}`

이것은 ziplist 안에서 다음과 같이 저장된다 :

`["us", "washington", "india", "delhi"]`

## CRC64 Check Sum

RDB 버전 5부터, 8byte CRC 64 체크섬(checksum)이 파일 끝에 추가되었다. redis.conf내의 파라미터를 통해서 이 체크섬을 비활성화시키는 것이 가능한다.
체크섬이 비활성화되면, 이 필드는 0이 될 것이다.