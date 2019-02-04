# RDB

### Check version of RDB file
- rdb파일에 대한 hexdump 실행 결과 첫 번째 라인의, REDIS*NNNN*에서 ***NNNN*** 이 RDB파일의 버전을 의미한다.
- rdb 파일 버전 히스토리에 대해서는 다음 링크를 참고한다.
    - https://github.com/sripathikrishnan/redis-rdb-tools/blob/master/docs/RDB_Version_History.textile
```
# REDIS0008 이므로, RDB버전은 8이 된다.
hexdump -C dump.rdb | head -n1
...
00000000  52 45 44 49 53 30 30 30  38 fa 09 72 65 64 69 73  |REDIS0008..redis|
```
