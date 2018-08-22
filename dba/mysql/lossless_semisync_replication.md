## Loss less Semisync Replication

### 5.6까지의 Semisync replication
1. 클라이언트로부터의 COMMIT이 요청됨
2. 스토리지 엔진부터 COMMIT이 시작되며, 이 단계를 PREPARE라고 부른다.
    - XA 트랜잭션의 PREPARE 단계
      - XA 트랜잭션은 스토리지엔진, 바이너리 로그를 묶어 실행되는 것
3. 바이너리 로그를 기록한다.
4. 스토리지 엔진으로 COMMIT이 완료된다.
5. Binlog Dump 스레드에 의해 바이너리 로그가 전송된다.
6. 슬레이브의 IO Thread에 의해 릴레이 로그가 기록된다.
7. 슬레이브는 Master로 ACK를 전송한다.
    - 이 시점에 슬레이브의 SQL Thread에 의해 릴레이 로그가 재생되는데,
    이것은 비동기 작업이므로 ACK 전송보다도 빠르게 처리될 수 있다.
8. Binlog Dump 스레드는 전달받은 ACK를 클라이언트 스레드로 전송한다.
9. 클라이언트 스레드는 OK패킷을 클라이언트에게 전송한다.

### 5.7.2 부터의 Lossless Semisync replication
1. 클라이언트로부터의 COMMIT이 요청됨
2. 스토리지 엔진부터 COMMIT이 시작되며, 이 단계를 PREPARE라고 부른다.
    - XA 트랜잭션의 PREPARE 단계
        - XA 트랜잭션은 스토리지엔진, 바이너리 로그를 묶어 실행되는 것
3. 바이너리 로그를 기록한다.
4. Binlog Dump 스레드에 의해 바이너리 로그가 전송된다.
5. 슬레이브의 IO Thread에 의해 릴레이 로그가 기록된다.
6. 슬레이브는 Master로 ACK를 전송한다.
  - 이 시점에 슬레이브의 SQL Thread에 의해 릴레이 로그가 재생되는데,
    - 이것은 비동기 작업이므로 ACK 전송보다도 빠르게 처리될 수 있다.
7. Binlog Dump 스레드는 전달받은 ACK를 클라이언트 스레드로 전송한다.
8. 스토리지 엔진으로 COMMIT이 완료된다.
9. 클라이언트 스레드는 OK패킷을 클라이언트에게 전송한다.
