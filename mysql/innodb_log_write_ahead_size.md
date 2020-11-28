---
tags: [mysql]
---

## read-on-write

innodb의 redo로그는 파일의 맨 뒷부분에 데이터를 추가해나가는 형식이 아니라, 하나 이상의 파일을 순환 형태로 재사용한다. 즉, 이미 데이터가 기록된 영역에 새로운 데이터를 계속해서 덮어 써나가는 것이다. 이러한 상황에서, redo log의 블럭 사이즈와 file system의 블럭 사이즈가 일치하지 않을 때, **read-on-write**라는 불필요한 동작이 발생할 수 있다.

innodb의 redo log block size는 512byte이고, 보통은 디바이스, 페이지 캐시 또는 file system의 블럭 사이즈(4kb) 보다는 작을 것이다. 이 때, 512byte의 redo로그의 블럭을 파일에 기록하려고 하려고 한다면, 아래와 같은 순서로 진행이 될 것이다.

1. os에서 해당 블럭에 대한 페이지를 파일 캐시에서 찾고, 만약 찾았다면 그 페이지에서 512byte를 수정한다.
2. 만약 파일 캐시에서 해당 영역을 찾지 못했다면, 파일시스템으로부터 해당 영역에 대해 읽기를 요청하게 되고, 4kb 단위로 블럭을 읽게 된다.
3. 읽어온 4kb의 블럭에서 512byte를 수정한다.

즉, 데이터를 쓰려는 영역에 이미 데이터가 남아 있으면, 새롭게 쓰려는 데이터가 512byte뿐이라도 4kb를 모두 읽어 필요한 부분을 수정해야하며, 바로 이것이 **read-on-write**이다. 오래된 데이터라서 덮어쓸 수 있다는 것은, 어디까지나 그 파일을 사용하는 어플리케이션(mysql)의 입장인 것이지, os입장에서는 그것이 오래된 데이터라서 버려도 되는 것인지 아닌지를 판단할 수가 없을 것이기 때문이다.

## innodb_log_write_ahead_size
MySQL 5.7 부터는 `innodb_log_write_ahead_size`라는 변수가 추가되어, redo 로그의 미리 쓰기 사이즈를 지정할 수가 있다.
- `innodb_log_write_ahead_size` (default 8192) 단위로 redo 로그 파일에 쓰기를 하는데,
- 새롭게 기록해야하는 데이터(512byte++) 이외에는 모두 0으로 채워 쓰기를 한다.

이처럼, 파일시스템의 블럭 사이즈 단위만큼 redo로그를 쓰게 되면, 기존 블럭을 모두 대체할 수가 있게 된다. 따라서, 기존 영역을 읽을 필요가 없어지므로 read-on-write와 같은 불필요한 동작도 사라지게 된다.

## Reference
- http://mysqlserverteam.com/mysql-5-7-improves-dml-oriented-workloads/
- https://dev.mysql.com/doc/refman/5.7/en/innodb-parameters.html#sysvar_innodb_log_write_ahead_size
- http://yoshinorimatsunobu.blogspot.com/2014/03/why-buffered-writes-are-sometimes.html