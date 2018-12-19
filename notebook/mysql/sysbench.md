# Sysbench 1.x

ref: https://github.com/akopytov/sysbench

## Installation
- RHEL/CentOS:
```bash
curl -s https://packagecloud.io/install/repositories/akopytov/sysbench/script.rpm.sh | sudo bash
sudo yum -y install sysbench
```

## Options
- tests 목록 확인
```bash
ls -lh /usr/share/sysbench/
```

- mysql 옵션
```bash
sysbench --help

...
General database options:

  --db-driver=STRING  specifies database driver to use ('help' to get list of available drivers) [mysql]
  --db-ps-mode=STRING prepared statements usage mode {auto, disable} [auto]
  --db-debug[=on|off] print database-specific debug information [off]
...
mysql options:
  --mysql-host=[LIST,...]          MySQL server host [localhost]
  --mysql-port=[LIST,...]          MySQL server port [3306]
  --mysql-socket=[LIST,...]        MySQL socket
  --mysql-user=STRING              MySQL user [sbtest]
  --mysql-password=STRING          MySQL password []
  --mysql-db=STRING                MySQL database name [sbtest]
  --mysql-ssl[=on|off]             use SSL connections, if available in the client library [off]
  --mysql-ssl-cipher=STRING        use specific cipher for SSL connections []
  --mysql-compression[=on|off]     use compression, if available in the client library [off]
  --mysql-debug[=on|off]           trace all client library calls [off]
  --mysql-ignore-errors=[LIST,...] list of errors to ignore, or "all" [1213,1020,1205]
  --mysql-dry-run[=on|off]         Dry run, pretend that all MySQL client API calls are successful without executing them [off]
  ```

- **oltp_read_write.lua**
```bash
sysbench /usr/share/sysbench/oltp_read_write.lua help
...
sysbench 1.0.15 (using bundled LuaJIT 2.1.0-beta2)

oltp_read_write.lua options:
  --auto_inc[=on|off]           Use AUTO_INCREMENT column as Primary Key (for MySQL), or its alternatives in other DBMS. When disabled, use client-generated IDs [on]
  --create_secondary[=on|off]   Create a secondary index in addition to the PRIMARY KEY [on]
  --delete_inserts=N            Number of DELETE/INSERT combinations per transaction [1]
  --distinct_ranges=N           Number of SELECT DISTINCT queries per transaction [1]
  --index_updates=N             Number of UPDATE index queries per transaction [1]
  --mysql_storage_engine=STRING Storage engine, if MySQL is used [innodb]
  --non_index_updates=N         Number of UPDATE non-index queries per transaction [1]
  --order_ranges=N              Number of SELECT ORDER BY queries per transaction [1]
  --pgsql_variant=STRING        Use this PostgreSQL variant when running with the PostgreSQL driver. The only currently supported variant is 'redshift'. When enabled, create_secondary is automatically disabled, and delete_inserts is set to 0
  --point_selects=N             Number of point SELECT queries per transaction [10]
  --range_selects[=on|off]      Enable/disable all range SELECT queries [on]
  --range_size=N                Range size for range SELECT queries [100]
  --secondary[=on|off]          Use a secondary index in place of the PRIMARY KEY [off]
  --simple_ranges=N             Number of simple range SELECT queries per transaction [1]
  --skip_trx[=on|off]           Don't start explicit transactions and execute all queries in the AUTOCOMMIT mode [off]
  --sum_ranges=N                Number of SELECT SUM() queries per transaction [1]
  --table_size=N                Number of rows per table [10000]
  --tables=N                    Number of tables [1]
```


## Usage
- prepare
```bash
sysbench /usr/share/sysbench/oltp_read_write.lua \
 --db-driver=mysql \
 --table-size=1000000 \
 --tables=10 \
 --mysql-host=__TARGET_HOST__ \
 --mysql-port=__TARGET_PORT__ \
 --mysql-user=sysbench \
 --mysql-password=sysbench \
 --mysql-db=sysbench \
 --threads=16 \
 prepare
```

- tests
```bash
sysbench /usr/share/sysbench/oltp_read_write.lua \
 --db-driver=mysql \
 --table-size=1000000 \
 --tables=10 \
 --mysql-host=__TARGET_HOST__ \
 --mysql-port=__TARGET_PORT__ \
 --mysql-user=sysbench \
 --mysql-password=sysbench \
 --mysql-db=sysbench \
 --db-ps-mode=disable \
 --threads=16 \
 run
```
