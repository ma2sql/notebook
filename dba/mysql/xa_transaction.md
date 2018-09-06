## XA Transaction
MySQL에서는 내부적으로 트랜잭션을 처리하는 과정에서, 스토리지 엔진에서의 로깅과 Binary Log를 기록하는 것을 XA 트랜잭션으로 관리한다.

### Phase1
1. XA TRANSACTION의 COMMIT 요청이 시작됨
2. 스토리지 엔진으로 커밋을 위한 PREPARE 요청
3. 이 단계가 성공하면 PHASE2로 넘어간다.
*이 단계에서 실패하면 ROLLBACK*
1. 바이너리 로그를 기록한다.
*이 단계에서 실패하면 역시 ROLLBACK이 발생할 듯. 기본적으로는 바이너리 로깅은 성공/실패 감시의 대상이 아닌가? 일단 넘어가자*

### Phase2
1. 바이너리 로그 기록이 정상이면 스토리지 엔진으로 COMMIT이 실행된다.
*이 지점에서 실패는 고려하지 않는다. 어차피 스토리지 엔진에 의해 영속성이 보장될거니까*
*또한, 앞선 과정을 무사히 잘 넘겨왔으니?*

### Crash & Recovery
1. 마지막 바이너리 로그를 열고, `Format_description`[^1] 이벤트를 찾는다.
2. `binlog-in-use` 플래그가 설정되어 있으면, 정상적으로 종료되지 못한 바이너리 로그라는 것으로 인식하고 XA Recovery를 시작
*정상적이면 그냥 여기서 종료될 듯*
3. 바이너리 로그에서 `xid events`를 읽고 모든 `XIDs` (XID 리스트)를 수집한다.
4. 스토리지 엔진은 PREPARE 상태(아직 COMMIT되지 않은 트랜잭션)인 트랜잭션의 XID가 `XIDs`에 포함되어 있다면 COMMIT을, 그렇지 않다면 ROLLBACK 시킨다.

### binlog-in-use flag
- flags는 총 16bit를 가지며, 이 안에서 binlog-in-use 이벤트는 **0x1**
즉, hexdump상에서는 `01`인 듯
```c++
libbinlogevents/include/binlog_event.h:
...
#define LOG_EVENT_BINLOG_IN_USE_F       0x1
```
추가: flags에서 자주보이는 `08`은 `USE`STATEMENT 사용인 듯
```c++
# Suppress the generation of 'USE' statements before the actual statement.
#define LOG_EVENT_SUPPRESS_USE_F    0x8
```
#### Server Crash
- *Flags의 binlog-in-use 플래그가 설정되어 있지 않음*
```
shell> pkill -9 mysql
shell> mysqlbinlog \
--force-if-open \
--hexdump \
--base64-output=never \
/mysql/MyHome/logs/binary_log.000001
...
#180906 12:52:00 server id 1  end_log_pos 120 CRC32 0x053b6783
# Position  Timestamp   Type   Master ID        Size      Master Pos    Flags
#        4 60 a4 90 5b   0f   01 00 00 00   74 00 00 00   78 00 00 00   01 00
#       17 04 00 35 2e 36 2e 31 37  2d 6c 6f 67 00 00 00 00 |..5.6.17.log....|
#       27 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
#       37 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
...
#       Start: binlog v 4, server v 5.6.17-log created 180906 12:52:00 at startup
# Warning: this binlog is either in use or was not closed properly.
ROLLBACK/*!*/;
DELIMITER ;
# End of log file
...
```
#### Normal Shutdown
- *Flags의 binlog-in-use 플래그가 설정되어 있지 않음*
```
shell> pkill -9 mysql
shell> mysqlbinlog \
--force-if-open \
--hexdump \
--base64-output=never \
/mysql/MyHome/logs/binary_log.000001
...
#180906 12:53:01 server id 1  end_log_pos 120 CRC32 0x32667ed3
# Position  Timestamp   Type   Master ID        Size      Master Pos    Flags
#        4 9d a4 90 5b   0f   01 00 00 00   74 00 00 00   78 00 00 00   00 00
#       17 04 00 35 2e 36 2e 31 37  2d 6c 6f 67 00 00 00 00 |..5.6.17.log....|
#       27 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
#       37 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 |................|
...
#       Start: binlog v 4, server v 5.6.17-log created 180906 12:53:01 at startup
ROLLBACK/*!*/;
# at 120
#180906 12:53:08 server id 1  end_log_pos 143 CRC32 0xeec9e5a1
# Position  Timestamp   Type   Master ID        Size      Master Pos    Flags
#       78 a4 a4 90 5b   03   01 00 00 00   17 00 00 00   8f 00 00 00   00 00
#       8b a1 e5 c9 ee                                      |....|
#       Stop
DELIMITER ;
# End of log file
...
```

### Travia
- 일반적인 개념의 트랜잭션이기보다는 스토리지 엔진, 바이너리 로그 간의 동기화를 위한 목적의 특수한 경우인 것으로 보임
- 스토리지 엔진의 성공 유무가 역시 중요하며, 바이너리 로그의 성공/실패에 따라 롤백이 결정
- 결국 데이터가 저장되는 곳은 스토리지 엔진이며, 바이너리 로그가 완전히 필수는 아니니까

[^1]: Format_description: 매 바이너리 로그 파일의 가장 첫 이벤트. "The first event of every binlog file is the Format_description event, which describes the server that wrote the file along with information about the contents and status of the file." [MySQL high availability 2nd edition. O'Reilly Media, p102]
