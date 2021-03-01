# tcpdump

## 주요 옵션
* `-tttt`: 각 덤프 라인마다 날짜, 시간, 분, 초, 초 미만의 단위의 타임스탬프를 출력한다.
* `-n`: 호스트 주소를 도메인으로 변환하지 않는다.
* `-nn`: 출력 결과의 프로토콜과 포트 번호를 변환없이 출력한다. (ex 80 -> http, 443 -> https). 아마도 `-n`의 기능도 포함한다.
* `-v`: TTL, 식별 정보, IP 패킷 내의 총 길이와 옵션 등의 정보를 모두 표기한다. (`-vv`, `-vvv` 등은 NFS, SMB, telnet 옵션 등을 추가적으로 표기해준다.)
* `-S`: 절대값 시퀀스 번호를 출력한다. (상대값이 아닌)

## Usage
- eth0, 6379포트로 들어오는 패킷을 ASCII 형태로 출력
```
tcpdump -i eth0 dst port 6379 -ttttnnSvA
```
- 레디스에서 MOVED 에러가 반환되는지 여부를 확인
```
tcpdump -i bond0 portrange __PORT_RANGE__ -ttttnnSvA | grep -i moved -B 5
```

## 참고
* https://linoxide.com/linux-how-to/14-tcpdump-commands-capture-network-traffic-linux/#13_Capture_both_incoming_and_outgoing_packets_of_a_specific_host