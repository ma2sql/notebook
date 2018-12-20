# Installation MySQL 8.0

Centos7 환경에서 MySQL 8.0을 설치하는 방법을 알아본다.
참고: https://dev.mysql.com/doc/refman/8.0/en/binary-installation.html


### 1. 설치
1. 필요한 패키지 설치
```bash
yum search libaio  # search for info
yum install libaio # install library
```

2. 유저 생성
```bash
groupadd mysql
useradd -r -g mysql -s /bin/false mysql
```

3. 바이너리 파일 다운로드 및 압축 해제
```bash
cd /usr/local

# 다운로드
wget https://cdn.mysql.com//Downloads/MySQL-8.0/mysql-8.0.13-linux-glibc2.12-x86_64.tar.xz

# 압축 해제
tar xvf mysql-8.0.13-linux-glibc2.12-x86_64.tar.xz

# full-path-to-mysql-VERSION-OS
ln -s $(pwd)/mysql-8.0.13-linux-glibc2.12-x86_64 mysql
```

4. 데이터 디렉터리 생성
```bash
mkdir -p /data/MYSQL
cd /data/MYSQL
mkdir data logs tmp

chown mysql:mysql -R .
chmod 750 -R .
```

5. 설정 파일 작성 ([my.cnf](#2-mycnf))
```bash
# Default options are read from the following files in the given order:
# /etc/my.cnf /etc/mysql/my.cnf /usr/local/mysql/etc/my.cnf ~/.my.cnf

vi ~/.my.cnf
```

6. mysql 데이터 초기화
```bash
# enter the command on a single line with the --defaults-file option first
/usr/local/mysql/bin/mysqld  --defaults-file=~/.my.cnf --initialize --user=mysql
/usr/local/mysql/bin/mysql_ssl_rsa_setup

# 초기 패스워드 확인
cat /data/MYSQL/logs/mysqld.err
...
[Server] A temporary password is generated for root@localhost: __INIT_PASSWORD__
```

7. 서비스 파일 생성
```bash
cp /usr/local/mysql/support-files/mysql.server /etc/init.d/mysql.server
```

8. MySQL 시작
```bash
/etc/init.d/mysql.server start
```

9. 디렉터리 확인
```bash
tree -L 2 /data/MYSQL

/data/MYSQL
├── data
│   ├── auto.cnf
│   ├── ca-key.pem
│   ├── ca.pem
│   ├── client-cert.pem
│   ├── client-key.pem
│   ├── ib_buffer_pool
│   ├── ibdata1
│   ├── ib_logfile0
│   ├── ib_logfile1
│   ├── ibtmp1
│   ├── #innodb_temp
│   ├── mysql
│   ├── mysql-80-001-db-common-jp2v-dev.pid
│   ├── mysql.ibd
│   ├── performance_schema
│   ├── private_key.pem
│   ├── public_key.pem
│   ├── server-cert.pem
│   ├── server-key.pem
│   ├── sys
│   ├── undo_001
│   └── undo_002
├── logs
│   ├── binary_log.000001
│   ├── binary_log.000002
│   ├── binary_log.index
│   └── mysqld.err
└── tmp
    ├── mysql.sock
    └── mysql.sock.lock

7 directories, 24 files
```

10. mysql 접속
```
/usr/local/mysql/bin/mysql -uroot -p
Enter password: __INIT__PASSWORD__
```

11. 초기 패스워드 변경
```sql
ALTER USER 'root'@'localhost' IDENTIFIED BY '__YOUR_PASSWORD__';
```

12. 환경 변수 수정
```bash
vi ~/.bash_profile
...
MYSQL_HOME=/usr/local/mysql

PATH=$PATH:$HOME/bin
PATH=$MYSQL_HOME/bin:$PATH

export PATH
...

# bash_profile 파일의 수정이 끝났으면, 실행
source ~/.bash_profile
```

### 2. my.cnf
우선 경로만 간단히 지정한 설정 파일을 만들고, 이를 사용하자.
그리고 나머지는 8.0을 연구하면서 천천히 추가해나가자.

```
[client]
port = 3306


[mysql]
no-auto-rehash
show-warnings


[mysqld]
server-id = 1
user    = mysql
port    = 3306

socket   = /data/MYSQL/tmp/mysql.sock
pid-file = /data/MYSQL/tmp/mysqld.pid

basedir = /usr/local/mysql
datadir = /data/MYSQL/data
tmpdir  = /data/MYSQL/tmp

log-bin     = /data/MYSQL/logs/binary_log
relay-log   = /data/MYSQL/logs/relay-log

log_error               = /data/MYSQL/logs/mysqld.err
general-log-file        = /data/MYSQL/logs/general_query.log
slow_query_log_file     = /data/MYSQL/logs/slow_query.log
```
