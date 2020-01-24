---
tags: [os, python]
---

# Unmap filesystem cache
마쓰노부 요시노리의 unmap script(https://github.com/yoshinorim/unmap_mysql_logs) 를 파이썬으로 구현할 수 있을 것 같아서 알아보니, 다음의 3가지 방법이 활용이 가능하다.

- ctypes를 이용한 커널 호출
- python-fadvise 모듈
- python3부터의 os.posix_fadvise

## ctypes를 이용한 unmap 구현
아래의 gist에서 활용한 내용으로, ctypes 모듈을 활용하여 c library를 로딩해서 사용한다. 직접 커널 함수를 호출하는 형식. 다만, POSIX_FADV_DONTNEED 값은 os 아키텍처에 따라 달라질 수도 있을 듯 한데, 이 부분을 조금만 주의하면 문제없이 사용가능할 것으로 생각한다.

*https://gist.github.com/dln/1027024*

```python
import ctypes
import ctypes.util

POSIX_FADV_DONTNEED = 4
libc = ctypes.CDLL(ctypes.util.find_library('c'))

def bufcache_dontneed(fd, offs, length):
    return libc.posix_fadvise(fd, ctypes.c_uint64(offs), ctypes.c_uint64(length), POSIX_FADV_DONTNEED)
```

## python-fadvise 모듈을 사용한 구현
fadvise 모듈을 이용해서 간단히 사용. 사용 방법에 대한 예제가 모듈 레포지토리에 안내되어 있지는 않으나, 매우 짧은 코드로 쓰기에는 무리가 없다. c로 작성된 모듈을 임포트해서 사용하는 형식.
https://github.com/lamby/python-fadvise

```python
from fadvise import dontneed
f = None
try:
    f = dontneed(filename, offset=0, len=0)
except IOError as e:
    print(e)
finally:
    if f: f.close()
```

## python3의 os (builtin)의 posix_fadvise
python 3.3 버전부터는 os 모듈에 posix_fadvise와 관련된 flag들이 추가되었다. 가장 좋은 방법이겠지만, python2의 환경에서는 활용할 수가 없다.

*https://docs.python.org/3/library/os.html#os.posix_fadvise*


```python
import os
fd = None
try:
    fd = os.open(filename, os.O_RDONLY)
    os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
except IOError as e:
    print(e)
finally:
    if f: f.close()
```

## 참고: posix_fadvise
파일의 데이터 접근에 대한 패턴을 미리 선언하는 함수. `POSIX_FADV_DONTNEED` 어드바이스 값을 부여해서 사용하는 경우, 특정 파일에 대한 페이지 캐시를 비우는 효과가 있다. `len`값을 0으로 부여하면 파일의 끝을 의미하게 되므로, `offset`과 `len`을 각각 0으로 지정해서 특정 파일에 대한 전체 캐시를 비울 수 있다. 반대로 0이 아닌 값을 지정해서 원하는 만큼만 캐시를 비우는 것도 가능하다.

```c
#include <fcntl.h>
int posix_fadvise(int fd, off_t offset, off_t len, int advice);
```