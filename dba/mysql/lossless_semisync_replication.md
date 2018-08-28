# Loss less Semisync Replication

## 5.6까지의 Semisync replication
![](https://github.com/ma2sql/notebook/blob/master/images/lossless_semisync_01.jpg)
1. 클라이언트로부터의 COMMIT이 요청됨
2. 클라이언트 스레드(커넥션 스레드)는 XA 트랜잭션을 위해 먼전 InnoDB 엔진으로 PREPARE를 실행한다.
3. 바이너리 로그를 기록한다.
4. InnoDB 엔진으로 COMMIT을 실행하며 XA 트랜잭션이 완료된다.
5. Binlog Dump 스레드에 의해 바이너리 로그가 슬레이브로 전송된다.
6. 전송된 바이너리 로그는 슬레이브의 IO Thread에 의해 릴레이 로그로 기록된다.
7. 슬레이브는 Master로 ACK를 전송한다.
    7-1. 슬레이브의 SQL Thread에 의해 릴레이로그가 재생되고 적용된다.
    7-2a. ACK를 마스터로 전송한다.
    7-2b. ACK를 클라이언트 스레드(커넥션 스레드)로 전송한다.
8. 최종적으로 클라이언트에게 OK패킷을 전송한다.

만약 위의 4번 단계가 완료되고, 바이너리가 미쳐 슬레이브로 전송되지 못한채 마스터가 크래시 되어버린다면?
*이미 마스터 상에서는 InnoDB엔진으로 커밋이 완료된 상태로, 이를 참조하는 어플리케이션이 있을 수 있다.* ***(Phantom Read)***

## 5.7.2 부터의 Lossless Semisync replication
![](https://github.com/ma2sql/notebook/blob/master/images/lossless_semisync_02.jpg)
1. 클라이언트로부터의 COMMIT이 요청됨
2. 클라이언트 스레드(커넥션 스레드)는 XA 트랜잭션을 위해 먼전 InnoDB 엔진으로 PREPARE를 실행한다.
3. 바이너리 로그를 기록한다.
4. Binlog Dump 스레드에 의해 바이너리 로그가 슬레이브로 전송된다.
5. 전송된 바이너리 로그는 슬레이브의 IO Thread에 의해 릴레이 로그로 기록된다.
6. 슬레이브는 Master로 ACK를 전송한다.
    6-1. 슬레이브의 SQL Thread에 의해 릴레이로그가 재생되고 적용된다.
    6-2a. ACK를 마스터로 전송한다.
    6-2b. ACK를 클라이언트 스레드(커넥션 스레드)로 전송한다.
7. InnoDB 엔진으로 COMMIT을 실행하며 XA 트랜잭션이 완료된다.
8. 최종적으로 클라이언트에게 OK패킷을 전송한다.

*슬레이브로 바이너리 로그를 전송하고 ACK를 받기전까지, InnoDB의 Commit은 완료되지 않는다.*
