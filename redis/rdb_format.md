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
FD $unsigned int            # FD는 "초 단위의 만료시간을 표기한다". 그 후, 만료 시간은 부호없는 4바이트의 정수로 읽힌다.
$value-type                 # 1 바이트 플래그는 값(value)의 타입을 표시한다. - set, map, sorted set 등등
$string-encoded-key         # 레디스 문자열(string)으로 인코딩된 키(key)
$encoded-value              # 값(value). 값의 타입($value-type)에 따라 다르다.
----------------------------
FC $unsigned long           # FC는 밀리초(ms)의 만료 시간을 나타낸다. 그 후, 만료 시간은 8바이트의 부호없는 long 타입으로 읽혀진다.
$value-type                 # 값(value)의 타입을 나타내는 1 바이트의 플래그. set, map, sorted set, etc..
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

다음 4바이트는 rdb 포맷의 버전 번호를 저장한다. 4바이트는 아스키 문자열로 해석된 다음, 정수형으로 변환되는데, 이때 문자열과 정수형 컨버전을 이용한다.

`00 00 00 03 # Version = 3`

### Database Selector

레디스 인스턴스는 여러 개의 데이터베이스를 보유할 수 있다.

단일 바이트 `0xFE`는 데이터베이스 선택자(selector)의 시작을 표시한다. 이 바이트 다음에, 변수 길이 필드는 데이터베이스 번호를 표시한다. 데이터베이스 번호를 읽는 방법을 이해하려면, 다음 섹션인 "[Length Encoding](#length-encoding)"을 참고하라.

### Key Value Pairs

데이터베이스 선택자 이후, rdb 파일은 키-값 쌍의 연속을 포함한다.

각 키-값 쌍은 4가지 부분으로 나뉜다 -

1. 키 만료시간의 타임스탬프. 선택적으로 포함
2. 값에 대한 타입을 표시하는 1바이트의 플래그
3. 레디스 문자열(Redis String)로 인코딩돤 키. "Redis String Encoding"를 참고
4. 값 타입(value type)에 따리 인코딩된 값. "Redis Value Encoding"를 참고

#### Key Expiry Timestamp

이 섹션은 1바이트의 플래그로 시작한다. `FD`는 만료 시간이 초 단위로 지정되었다는 것을 나타낸다. `FC`는 만료 시간이 밀리초 단위로 지정되었다는 것을 나타낸다.

만약 시간이 밀리초로 지정된다면, 다음 8바이트는 유닉스 타임(unix time)을 표현한다. 이 숫자는 초 또는 밀리초 정밀도의 유닉스 타임스탬프 (unix timestamp)이고, 이 키의 만료 시간을 나타낸다.

이 숫자가 인코딩되는 방법에 관해서는 "Redis Length Encoding" 섹션을 참고하라.

임포트 프로세스동안, 만료된 키는 폐기될 것이다.

#### Value Type

이 1 바이트 플래그는 값을 저장하기 위해 사용되는 인코딩을 나타낸다.

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

길이 인코딩(Length encoding)은 스트림 내의 다음 오브젝트의 길이를 저장하는데 사용된다. 길이 인코딩은 가능한 한 더 적은 바이트를 사용하도록 설계된 변수 바이트 인코딩이다.

이것은 길이 인코딩이 동작하는 방법이다:

1. 스트림으로부터 1바이트를 읽어, 최상위(most significant bits) 2비트를 읽는다.
2. `00`으로 시작하면, 그 다음 6비트는 길이를 나타낸다.
3. `01`로 시작하면, 스트림으로부터 추가적인 바이트를 읽어야한다. 조합된 14비트로 길이를 나타낸다.
4. `10`으로 시작하면, 나머지 6비트는 버려진다. 스트림으로부터 추가적으로 4바이트를 읽고, 이 4바이트가 길이(RDB의 버전이 6에서는 빅 엔디안 포맷)를 나타낸다. 
5. `11`로 시작하며느 다음 오브젝트는 특별한 포맷으로 인코딩된다. 나머지 6비트는 이 포맷을 표시한다. 이 인코딩은 일반적으로 숫자를 문자열로 저장하거나, 인코딩된 문자열을 저장하기 위해 사용된다. "[String Encoding](#string-encoding)"을 참고

이 인코딩의 결과로 -

1. 63을 포함하는 숫자까지, 1바이트러 저장할 수 있다.
2. 16383을 포함하는 숫자까지, 2바이트로 저장할 수 있다.
3. 2^32-1을 포함하는 숫자까지는 5바이트로 저장할 수 있다.

## String Encoding

레디스 문자열(Redis Strings)은 바이너리에 안전하다. 이것은 무엇이든 레디스 문자열로 저장할 수 있다는 것을 의미한다. 어떤 특별한 end-of-string 토큰을 가지지 않는다. 레디스 문자열은 바이트의 배열로 생각하는 것이 가장 좋다.

레디스에는 세 가지 타입의 문자열이 있다 -

1. 길이 접두사 문자열(Integers as String)
2. 8, 16, 또는 32비트의 정수
3. LZF로 압축된 문자열

#### Length Prefixed String

길이가 접두사 문자열은 매우 간단하다. 바이트로된 문자열의 길이는 먼저 "길이 인코딩(Length Encoding)"을 이용해서 인코딩된다. 이 이후에, 문자열의 원시 바이트(raw bytes)가 저장된다.

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
3. 그 다음 `clen` 바이트를 스트림에서 읽는다.
4. 마지막으로, 이 바이트들을 LZF 알고리즘을 이용해서 압축을 해제한다.

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

1. *zmlen* : 1 바이트 길이이다. zipmap의 크기를 가지고 있는 1바이트의 길이이다. 만약, 254과 같거나 크다면, 이 값은 사용되지 않는다. 길이를 찾으려면 zipmap 전체를 순회해야한다.
2. *len* : 이어지는 문자열의 길이이다. 그리고 이 문자열은 키 또는 값이 될 수가 있다. 이 길이는 1 바이트 또는 5 바이트("길이 인코딩 (Length Encoding)"과는 다르다)로 저장된다. 만약, 첫 바이트가 0에서 252사이라면, 그것은 zipmap의 길이이다. 만약, 첫 바이트가 253이면, 그 다음 4바이트를 zipmap의 길이를 나타내는 부호 없는 정수형으로 읽는다. 254에서 255는 이 필드에서 유효하지 않은 값이다.
3. *free* : 이것은 항상 1바이트이며, 값(value) 이후의 여유 공간 (free 바이트)의 수를 나타낸다. 예를 들어, 한 키의 값이 "America"이고, 이것이 "USA"로 업데이트된다면, 4바이트의 여유 공간이 사용 가능하게 된다.
4. *zmend* : 항상 255. zipmap의 끝을 나타낸다.


*Worked Example*

`18 02 06 4d 4b 44 31 47 36 01 00 32 05 59 4e 4e 58 4b 04 00 46 37 54 49 ff ..`

1. "문자열 인코딩 (String Encoding)"을 이용한 디코딩으로 시작된다. `18`은 문자열의 길이라는 것을 알 수 있다. 따라서, 우리는 그 다음 24바이트를 읽을 것이고, 즉(i.e.) `ff`까지이다.
2. 이제, 우리는 "Zipmap Encoding"을 이용해서 `02 06... `으로 시작하는 문자열을 분석할 것이다.
3. `02`는 해시맵내의 엔트리 수이다.
4. `06`은 다음 문자열의 길이이다. 254보다 작기 때문에, 추가적인 바이트를 읽지 않아도 된다.
5. 다음 6바이트, 즉`4d 4b 44 31 47 36` 를 읽고, 키(key) "MKD1G6"을 얻는다.
6. `01`은 다음 문자열인 값(value)의 길이이다.
7. `00`은 여유(free) 바이트의 길이이다.
8. 다음 1바이트, `0x32`를 읽는다. 그래서 값 "2"를 얻는다.
9. 이 경우, 여유 바이트는 0이고, 그래서 우리는 어떤것도 생략하지 않는다.
10. `05`는 다음 문자열의 길이이고, 이 경우에는 키(key)이다.
11. 다음 5바이트 `59 4e 4e 58 4b`를 읽고, 키(key) "YNNXK"를 언든다.
12. `04` is the length of the next string, which is a value
12. `04`는 다음 문자열인 값(value)의 길이이다.
13. `00`은 값(value) 이후의 여유(free) 바이트의 수이다.
14. 그 다음 4바이트, 즉 `46 37 54 49`를 읽고, 값 "F7TI"를 얻는다.
15. 마지막으로, `FF`를 만나게 되고, 이것은 zipmap의 끝을 의미한다.
16. 그러므로, 이 zipmap은 해시 `{"MKD1G6" => "2", "YNNXK" => "F7TI"}`를 표현한다.

## Ziplist Encoding

A Ziplist is a list that has been serialized to a string. In essence, the elements of the list are stored sequentially along with flags and offsets to allow efficient traversal of the list in both directions.

To parse a ziplist, first a string is read from the stream using "String Encoding". This string is the envelope of the ziplist. The contents of this string represent the ziplist.

The structure of a ziplist within this string is as follows -

`<zlbytes><zltail><zllen><entry><entry><zlend>`

1. *zlbytes* : This is a 4 byte unsigned integer representing the total size in bytes of the zip list. The 4 bytes are in little endian format - the least signinficant bit comes first.
2. *zltail* : This is a 4 byte unsigned integer in little endian format. It represents the offset to the tail (i.e. last) entry in the zip list
3. *zllen* : This is a 2 byte unsigned integer in little endian format. It represents the number of entries in this zip list
4. *entry* : An entry represents an element in the zip list. Details below
5. *zlend* : Is always equal to `255`. It represents the end of the zip list.

Each entry in the zip list has the following format :

`<length-prev-entry><special-flag><raw-bytes-of-entry>`

*length-prev-entry* : This field stores the length of the previous entry, or 0 if this is the first entry. This allows easy traversal of the list in the reverse direction. This length is stored in either 1 byte or in 5 bytes. If the first byte is less than or equal to 253, it is considered as the length. If the first byte is 254, then the next 4 bytes are used to store the length. The 4 bytes are read as an unsigned integer.

*Special flag* : This flag indicates whether the entry is a string or an integer. It also indicates the length of the string, or the size of the integer. 
The various encodings of this flag are shown below :

1. |00pppppp| - 1 byte : String value with length less than or equal to 63 bytes (6 bits).
2. |01pppppp|qqqqqqqq| - 2 bytes : String value with length less than or equal to 16383 bytes (14 bits).
3. |10______|qqqqqqqq|rrrrrrrr|ssssssss|tttttttt| - 5 bytes : String value with length greater than or equal to 16384 bytes.
4. |1100____| - Read next 2 bytes as a 16 bit signed integer
5. |1101____| - Read next 4 bytes as a 32 bit signed integer
6. |1110____| - Read next 8 bytes as a 64 bit signed integer
7. |11110000| - Read next 3 bytes as a 24 bit signed integer
8. |11111110| - Read next byte as an 8 bit signed integer
9. |1111xxxx| - (with xxxx between 0000 and 1101) immediate 4 bit integer. Unsigned integer from 0 to 12. The encoded value is actually from 1 to 13 because 0000 and 1111 can not be used, so 1 should be subtracted from the encoded 4 bit value to obtain the right value.

*Raw Bytes* : After the special flag, the raw bytes of entry follow. The number of bytes was previously determined as part of the special flag.

*Worked Example 1*

```
23 23 00 00 00 1e 00 00 00 04 00 00 e0 ff ff ff ff ff ff ff 7f 0a d0 ff ff 00 00 06 c0 fc 3f 04 c0 3f 00 ff ... 
  |           |           |     |                             |                 |           |           |       

```

1. Start by decoding this using "String Encoding". `23` is the length of the string, therefore we will read the next 35 bytes till `ff`
2. Now, we are parsing the string starting at `23 00 00 ...` using "Ziplist encoding"
3. The first 4 bytes `23 00 00 00` represent the total length in bytes of this ziplist. Notice that this is in little endian format
4. The next 4 bytes `1e 00 00 00` represent the offset to the tail entry. `1e` = 30, and this is a 0 based offset. 0th position = `23`, 1st position = `00` and so on. It follows that the last entry starts at `04 c0 3f 00 ..`
5. The next 2 bytes `04 00` represent the number of entries in this list.
6. From now on, we start reading the entries
7. `00` represents the length of previous entry. 0 indicates this is the first entry.
8. `e0` is the special flag. Since it starts with the bit pattern `1110____`, we read the next 8 bytes as an integer. This is the first entry of the list.
9. We now start the second entry
10. `0a` is the length of the previous entry. 10 bytes = 1 byte for prev. length + 1 byte for special flag + 8 bytes for integer.
11. `d0` is the special flag. Since it starts with the bit pattern `1101____`, we read the next 4 bytes as an integer. This is the second entry of the list
12. We now start the third entry
13. `06` is the length of previous entry. 6 bytes = 1 byte for prev. length + 1 byte for special flag + 4 bytes for integer
14. `c0` is the special flag. Since it starts with the bit pattern `1100____`, we read the next 2 bytes as an integer. This is the third entry of the list
15. We now start the last entry
16. `04` is length of previous entry
17. `c0` indicates a 2 byte number
18. We read the next 2 bytes, which gives us our fourth entry
19. Finally, we encounter `ff`, which tells us we have consumed all elements in this ziplist.
20. Thus, this ziplist stores the values `[0x7fffffffffffffff, 65535, 16380, 63]

## Intset Encoding

An Intset is a binary search tree of integers. The binary tree is implemented in an array of integers. An intset is used when all the elements of the set are integers. An Intset has support for upto 64 bit integers. As an optimization, if the integers can be represented in fewer bytes, the array of integers will be constructed from 16 bit or 32 bit integers. When a new element is inserted, the implementation takes care to upgrade if necessary.

Since an Intset is a binary search tree, the numbers in this set will always be sorted.

An Intset has an external interface of a Set. 

To parse an Intset, first a string is read from the stream using "String Encoding". This string is the envelope of the Intset. The contents of this string represent the Intset.

Within this string, the Intset has a very simple layout :

`<encoding><length-of-contents><contents>`

1. *encoding* : is a 32 bit unsigned integer. It has 3 possible values - 2, 4 or 8. It indicates the size in bytes of each integer stored in contents. And yes, this is wasteful - we could have stored the same information in 2 bits.
2. *length-of-contents* : is a 32 bit unsigned integer, and indicates the length of the contents array
3. *contents* : is an array of $length-of-contents bytes. It contains the binary tree of integers

*Example*

`14 04 00 00 00 03 00 00 00 fc ff 00 00 fd ff 00 00 fe ff 00 00 ...`

1. Start by decoding this using "String Encoding". `14` is the length of the string, therefore we will read the next 20 bytes till `00`
2. Now, we start interpreting the string starting at `04 00 00 ... `
3. The first 4 bytes `04 00 00 00` is the encoding. Since this evaluates to 4, we know we are dealing with 32 bit integers
4. The next 4 bytes `03 00 00 00` is the length of contents. So, we know we are dealing with 3 integers, each 4 byte long
5. From now on, we read in groups of 4 bytes, and convert it into a unsigned integer
6. Thus, our intset looks like - `0x0000FFFC, 0x0000FFFD, 0x0000FFFE`. Notice that the integers are in little endian format i.e. least significant bit came first.

## Sorted Set as Ziplist Encoding

A sorted list in ziplist encoding is stored just like the Ziplist described above. Each element in the sorted set is followed by its score in the ziplist.

*Example*

['Manchester City', 1, 'Manchester United', 2, 'Tottenham', 3]

As you see, the scores follow each element.

## Hashmap in Ziplist Encoding

In this, key=value pairs of a hashmap are stored as successive entries in a ziplist. 

Note : This was introduced in rdb version 4. This deprecates zipmap encoding that was used in earlier versions.

*Example*

   {"us" => "washington", "india" => "delhi"} 

   is stored in a ziplist as :

   ["us", "washington", "india", "delhi"]

## CRC64 Check Sum

Starting with RDB Version 5, an 8 byte CRC 64 checksum is added to the end of the file. It is possible to disable this checksum via a parameter in redis.conf.
When checksum is disabled, this field will have zeroes.