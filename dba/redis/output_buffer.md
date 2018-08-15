### Output Buffer
- 클라이언트의 요청에 대한 결과를 바로 클라이언트에게 전달하는 것이 아닌, Output Buffer에 추가해두고 비동기적으로 전송하는 것으로 보임
- 코드 내에서는 addReply라는 함수가 지속적으로 호출되고, 이 것이 바로 처리 결과를 즉시 클라이언트에게 return하는 것이 아니라, output 버퍼에 담아두는 역할을 한다.
  - 아마도 비동기적인 처리 흐름을 가져가기 위한 것으로 보인다.
  - 특정한 타이밍에 일괄적으로 보내는 것으로 보인다.  
- Replication 시에도 이는 마찬가지인데,
  - Replication이 시작되면 BGSAVE에 의해 RDB가 수행된다.
    - *RDB의 slave 전송 시점에 output buffer를 사용하는지는 아직 알 수가 없다.*
    - 이 시점부터의 write 요청은 아마도 client(slave)의 output buffer에 저장되기 시작할 것이고,
    - slave가 RDB에 대한 loading을 마치면, output buffer의 내용을 전달받기 시작할 것이다.
    - 참고: Replication에는 크게 2-3가지의 흐름이 있다.
      1. 자신의 Local에 BGSAVE를 통해 RDB를 남긴다.
      2. RDB를 slave로 전송한다. (slave에서 가져가는 것인지, master에서 전송해주는 것인지는 아직 모름)
      3. slave에서는 RDB를 loading한다.
        - *RDB를 socket으로 바로 slave로 전송하는 경우, 1-2번이 합쳐지겠지..*
- 이 Buffer에 대한 상한값을 지정하는 것이 client-output-buffer-limit 변수인데,
- Replication 시점에 이 변수의 상한값으로 인해 output buffer가 flush된다면, Full Sync를 다시 시도하게 될 것이다.
- 최악의 경우는 이 것이 지속적으로 반복되어, 매우 잦은 RDB를 유발할 수 있다.
- 따라서, client-output-buffer-limit 변수는 replication 수행 시간을 적절히 예측하고,
- 그 시간 사이에 발생하는 write요청의 양을 충분히 output buffer에 담을 수 있도록
- 넉넉한 크기를 지정해둘 필요가 있다.
