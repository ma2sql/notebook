# Mrooga 7.0.9 Variables

### 3.1 mroonga_action_on_fulltext_query_error
전문 검색 쿼리 에러의 동작 방식
`mroonga_action_on_fulltext_query_error`의 기본값은 `ERROR_AND_LOG`입니다. 이것은 종래의 mroonga와 같은 동작 방식입니다.
사용 가능한 값은 아래와 같습니다.

Variable | Description
---------|-------------
ERROR | 에러를 보고한다. 로그는 출력하지 않는다.
ERROR_AND_LOG | 에러를 보고한다. 로그 역시 출력한다. (기본값)
IGNORE | 에러를 무시한다. 로그도 출력하지 않는다.
IGNORE_AND_LOG | 에러를 무시하지만, 로그는 출력한다. (InnoDB와 비슷한 동작 방식)

```sql
mysql> SHOW VARIABLES LIKE 'mroonga_action_on_fulltext_query_error';
+----------------------------------------+---------------+
| Variable_name                          | Value         |
+----------------------------------------+---------------+
| mroonga_action_on_fulltext_query_error | ERROR_AND_LOG |
+----------------------------------------+---------------+
1 row in set (0.00 sec)
```

### 3.2 mroonga_boolean_mode_syntax_flags
`MATCH () AGAINST ('...' IN BOOLEAN MODE)`의 구문을 커스터마이팅하는 플래그
이 변수는 시스템 글로벌/세션 각각 적용 가능하다.

Flag | Description
-----|-------------
DEFAULT | `SYNTAX QUERY, ALLOW_LEADING_NOT`과 같습니다.
SYNTAX_QUERY | Grooga 쿼리 구문. Groonga의 쿼리 구문은 MySQL의 BOOLEAN MODE의 구문과 호환성이 있습니다.<br> SYNTAX_QUERY과 SYNTAX_SCRIPT 중에서 어느 쪽도 지정하지 않는 경우에는 SYNTAX_QUERY이 지정된 것으로 인식합니다.
ALLOW_COLUMN | 쿼리 구문으로 `COLUMN:...`와 같은 구문을 사용할 수 있도록 합니다. 이것은 MySQL의 BOOLEAN MODE의 구문과 호환성이 없습니다.<br>이 구문을 사용하면 하나의 `MATCH () AGAINTST ()`의 안에서 복수의 인덱스를 사용할 수 있습니다. MySQL은 하나의 쿼리의 안에서 하나의 인덱스만 사용할 수 있습니다. 이 구문을 사용하여 이러한 제한을 회피할 수 있습니다.
ALLOW_UPDATE | 쿼리 구문의 안에서 값을 갱신하는 `COLUMN:=NEW_VALUE`라는 구문을 사용할 수 있도록 합니다.
ALLOW_LEADING_NOT | 쿼리 구문에서 `-NOT_INCLUDE_KEYWORD ...` 구문을 사용할 수 있도록 합니다.

```sql
mysql> SET mroonga_boolean_mode_syntax_flags = "SYNTAX_SCRIPT";
```
### 3.3 mroonga_database_path_prefix
TODO

### 3.4 mroonga_default_parser
버전 5.04에서 비권장: Use [mroonga_default_tokenizer](#3.4-mroonga_default_tokenizer) instead.
기본값은 전문검색 파서. 기본값은 configure의 `with-default-parser` 옵션으로 지정할 수 있습니다. (지정하지 않는 경우에는 `TokenBigram`).

전문 검색 파서로서 `TokenBiagramSplitSymbolAlphaDigit`을 사용하는 예입니다. 이 예에서는 `body_index` 전문 검색 인덱스는 `TokenBiagramSplitSymbolAlphaDigit`을 사용합니다.

```sql
SET GLOBAL mroonga_default_parser=TokenBigramSplitSymbolAlphaDigit;
CREATE TABLE diaries (
  id INT PRIMARY KEY AUTO_INCREMENT,
  body TEXT,
  FULLTEXT INDEX body_index (body)
) DEFAULT CHARSET UTF8;
```

### 3.5 mroonga_default_tokenizer
버전 5.04에서 추가.

전문 검색 용의 기본 토크나이저. 기본값은 configure의 --with-default-tokenizer=TOKENIZER 옵션으로 지정할 수 있습니다. 이 옵션을 지정하지 않으면 `TokenBiagram`이 지정됩니다.

전문 검색용 인덱스의 토크나이저로서 `TokenBiagramSplitSymbolAlphaDigit`을 사용하는 예 입니다. 이 예에서는 `body_index` 전문 검색 인덱스는 `TokenBiagramSplitSymbolAlphaDigit`을 사용합니다.

```sql
SET GLOBAL mroonga_default_tokenizer=TokenBigramSplitSymbolAlphaDigit;
CREATE TABLE diaries (
  id INT PRIMARY KEY AUTO_INCREMENT,
  body TEXT,
  FULLTEXT INDEX body_index (body)
) DEFAULT CHARSET UTF8;
```

### 3.6 mroonga_default_wrapper_engine
TODO

### 3.7 mroonga_dry_write
Groonga 데이터베이스에 실제 데이터를 쓸 지를 지정합니다. 기본값은 `OFF`로, 실제로 groonga 데이터베이스에 데이터를 기록합니다. 통상은 이 값을 변경할 필요는 없습니다. 이 변수는 벤치마크 테스트 시점에 편리합니다. 이 값을 `ON`으로 두는 것으로 MySQL과 Mroonga만의 처리 시간을 계측하는 것이 가능합니다. 이 시간에는 Groonga의 처리 시간은 포함되지 않습니다.

```sql
mysql> SHOW VARIABLES LIKE 'mroonga_dry_write';
+-------------------+-------+
| Variable_name     | Value |
+-------------------+-------+
| mroonga_dry_write | OFF   |
+-------------------+-------+
1 row in set (0.00 sec)

mysql> SET mroonga_dry_write = true;
Query OK, 0 rows affected (0.00 sec)

mysql> SHOW VARIABLES LIKE 'mroonga_dry_write';
+-------------------+-------+
| Variable_name     | Value |
+-------------------+-------+
| mroonga_dry_write | ON    |
+-------------------+-------+
1 row in set (0.00 sec)
```

### 3.8 mroonga_enable_optimization
최적화를 설정할지 여부를 지정합니다. 기본값은 `ON`으로 최적화를 적용하도록 되어 있습니다. 통상은 이 값을 변경할 필요는 없습니다. 이 옵션은 벤치마크 시점에 편리합니다.

```sql
mysql> SHOW VARIABLES LIKE 'mroonga_enable_optimization';
+-----------------------------+-------+
| Variable_name               | Value |
+-----------------------------+-------+
| mroonga_enable_optimization | ON    |
+-----------------------------+-------+
1 row in set (0.00 sec)

mysql> SET mroonga_enable_optimization = false;
Query OK, 0 rows affected (0.00 sec)

mysql> SHOW VARIABLES LIKE 'mroonga_enable_optimization';
+-----------------------------+-------+
| Variable_name               | Value |
+-----------------------------+-------+
| mroonga_enable_optimization | OFF   |
+-----------------------------+-------+
1 row in set (0.00 sec)
```

### 3.9 mroonga_libgroonga_support_lz4
Groonga 라이브러리의 LZ4 지원 여부

```sql
mysql> SHOW GLOBAL VARIABLES LIKE 'mroonga_libgroonga_support_lz4';
+--------------------------------+-------+
| Variable_name                  | Value |
+--------------------------------+-------+
| mroonga_libgroonga_support_lz4 | ON    |
+--------------------------------+-------+
```

### 3.10 mroonga_libgroonga_support_zlib
Groonga 라이브러리의 zlib 지원 여부

```sql
mysql> SHOW GLOBAL VARIABLES LIKE 'mroonga_libgroonga_support_zlib';
+---------------------------------+-------+
| Variable_name                   | Value |
+---------------------------------+-------+
| mroonga_libgroonga_support_zlib | ON    |
+---------------------------------+-------+
```

### 3.11 mroonga_libgroonga_support_zstd
Groonga 라이브러리의 Zstandard 지원 여부

```sql
mysql> SHOW GLOBAL VARIABLES LIKE 'mroonga_libgroonga_support_zstd';
+---------------------------------+-------+
| Variable_name                   | Value |
+---------------------------------+-------+
| mroonga_libgroonga_support_zstd | ON    |
+---------------------------------+-------+
```

### 3.12 mroonga_libgroonga_version
groonga의 라이브러리 버전

```sql
mysql> SHOW VARIABLES LIKE 'mroonga_libgroonga_version';
+----------------------------+------------------+
| Variable_name              | Value            |
+----------------------------+------------------+
| mroonga_libgroonga_version | 1.2.8-9-gbf05b82 |
+----------------------------+------------------+
1 row in set (0.00 sec)
```

### 3.13 mroonga_lock_timeout
TODO

### 3.14 mroonga_log_file
Mroonga의 로그 파일명. 기본값은 `groonga.log`.

```sql
mysql> SHOW VARIABLES LIKE 'mroonga_log_file';
+------------------+-------------+
| Variable_name    | Value       |
+------------------+-------------+
| mroonga_log_file | groonga.log |
+------------------+-------------+
1 row in set (0.00 sec)

mysql> SET GLOBAL mroonga_log_file = "/tmp/mroonga.log";
Query OK, 0 rows affected (0.00 sec)

mysql> SHOW VARIABLES LIKE 'mroonga_log_file';
+------------------+------------------+
| Variable_name    | Value            |
+------------------+------------------+
| mroonga_log_file | /tmp/mroonga.log |
+------------------+------------------+
1 row in set (0.00 sec)
```

### 3.15 mroonga_log_level
Mroonga의 로그의 출력 레벨. 기본값은 `NOTICE`.
다음은 사용 가능한 `mroonga_log_level`의 리스트이다.

Log Level | Description
---------|------------
NONE | 로그를 출력하지 않음.
EMERGE | 데이터베이스의 파손 등의 긴급한 처리가 필요한 로그 메시지를 출력한다.
ALERT | 내부적인 에러를 표시하는 로그를 출력한다.
CRIT | 데드락의 발생 등 치명적인 로그 메시지를 출력한다.
ERROR | Mroonga를 사용하고 있는 API의 에러 로그 메시지를 출력한다.
WARNING | 잘못 지정된 인수등의 경고 로그 메시지를 출력한다.
NOTICE | 설정이나 상태의 변화를 표시하는 로그 메시지를 출력한다.
INFO | 파일 조작 등의 정보를 로그 메시지로 표시한다.
DEBUG | 디버그 메시지를 출력한다.<br> Mroonga개발자나 버그 리포팅의 경우에 추천합니다.
DUMP | 테스트툴 대상의 덤프 메시지를 출력합니다.

```sql
mysql> SHOW VARIABLES LIKE 'mroonga_log_level';
+-------------------+--------+
| Variable_name     | Value  |
+-------------------+--------+
| mroonga_log_level | NOTICE |
+-------------------+--------+
1 row in set (0.00 sec)

mysql> SET GLOBAL mroonga_log_level = "debug";
Query OK, 0 rows affected (0.00 sec)

mysql> SHOW VARIABLES LIKE 'mroonga_log_level';
+-------------------+-------+
| Variable_name     | Value |
+-------------------+-------+
| mroonga_log_level | DEBUG |
+-------------------+-------+
1 row in set (0.00 sec)
```

### 3.16 mroonga_match_escalation_thresh
매치 방법을 에스컬레이션 할지 여부를 결정하는 역치이다. 매치 방법에 대해서는 [Groonga  검색 사양(일본어)](http://groonga.org/docs/spec/search.html)를 참고할 것.

기본값은 Groonga의 기본값과 같다. 기본 설정으로 인스톨한 경우에는 `0`이 된다. 이 변수의 스코프는 `Global`과 `Session` 양쪽 모두로, my.cnf 또는 `SET GLOBAL mroonga_match_escalation_threshold = THRESHOLD;`로 기본값을 설정할 수 있다.

매치 방법이 에스컬레이션 될 지 여부를 결정하는 역치로 -1을 지정하는 예. (-1은 절대 에스컬레이션을 하지 않겠다는 의미)
```sql
SET GLOBAL mroonga_match_escalation_threshold = -1;
```
이 변수 값에 의해 동작 방식의 변화를 나타내는 별도의 예이다.

```sql
CREATE TABLE diaries (
  id INT PRIMARY KEY AUTO_INCREMENT,
  title TEXT,
  tags TEXT,
  FULLTEXT INDEX tags_index (tags) COMMENT 'parser "TokenDelimit"'
) ENGINE=mroonga DEFAULT CHARSET=UTF8;

-- Test data
INSERT INTO diaries (title, tags) VALUES ("Hello groonga!", "groonga install");
INSERT INTO diaries (title, tags) VALUES ("Hello mroonga!", "mroonga install");

-- Matches all records that have "install" tag.
SELECT * FROM diaries WHERE MATCH (tags) AGAINST ("install" IN BOOLEAN MODE);
-- id        title   tags
-- 1 Hello groonga!  groonga install
-- 2 Hello mroonga!  mroonga install

-- Matches no records by "gr" tag search because no "gr" tag is used.
-- But matches a record that has "groonga" tag because search
-- method is escalated and prefix search with "gr" is used.
-- The default threshold is 0. It means that no records are matched then
-- search method is escalated.
SELECT * FROM diaries WHERE MATCH (tags) AGAINST ("gr" IN BOOLEAN MODE);
-- id        title   tags
-- 1 Hello groonga!  groonga install

-- Disables escalation.
SET mroonga_match_escalation_threshold = -1;
-- No records are matched.
SELECT * FROM diaries WHERE MATCH (tags) AGAINST ("gr" IN BOOLEAN MODE);
-- id        title   tags

-- Enables escalation again.
SET mroonga_match_escalation_threshold = 0;
-- Matches a record by prefix search with "gr".
SELECT * FROM diaries WHERE MATCH (tags) AGAINST ("gr" IN BOOLEAN MODE);
-- id        title   tags
-- 1 Hello groonga!  groonga install
```

### 3.17 mroonga_max_n_records_for_estimate
버전 5.02에서 추가
TODO

### 3.18 mroonga_enable_operations_recording
리커버리를 위해 오퍼레이션을 기록할지 여부를 설정하는 변수.
기본값은 `ON`으로 되어 있고, 이것은 오퍼레이션을 Groonga 데이터베이스 기록하는 것을 의미한다.
변경된 설정을 반영하기 위해서는 `FLUSH TABLES` 명령으로 다시 데이터베이스를 열(reopen) 필요가 있다.

```sql
mysql> SET GLOBAL mroonga_enable_operations_recording = false;
Query OK, 0 rows affected (0.00 sec)

mysql> FLUSH TABLES;
Query OK, 0 rows affected (0.00 sec)

mysql> SHOW GLOBAL VARIABLES LIKE 'mroonga_enable_operations_recording';
+-------------------------------------+-------+
| Variable_name                       | Value |
+-------------------------------------+-------+
| mroonga_enable_operations_recording | OFF   |
+-------------------------------------+-------+
```


### 3.19 mroonga_vector_column_delimiter
벡터 컬럼을 출력할 때의 구분자 문자. 기본값은 공백이다.

```sql
mysql> SHOW VARIABLES LIKE 'mroonga_vector_column_delimiter';
+---------------------------------+-------+
| Variable_name                   | Value |
+---------------------------------+-------+
| mroonga_vector_column_delimiter |       |
+---------------------------------+-------+
1 row in set (0.00 sec)


mysql> SET GLOBAL mroonga_vector_column_delimiter = ';';
Query OK, 0 rows affected (0.00 sec)

mysql> SHOW GLOBAL VARIABLES LIKE 'mroonga_vector_column_delimiter';
+---------------------------------+-------+
| Variable_name                   | Value |
+---------------------------------+-------+
| mroonga_vector_column_delimiter | ;     |
+---------------------------------+-------+
```

### 3.20 mroonga_version
Mroonga의 버전.

```sql
mysql> SHOW VARIABLES LIKE 'mroonga_version';
+-----------------+-------+
| Variable_name   | Value |
+-----------------+-------+
| mroonga_version | 1.10  |
+-----------------+-------+
1 row in set (0.00 sec)
```

### 3.21 mroonga_condition_push_down_type
버전 7.10에서 추가.

컨디션 푸시 다운 서포트를 어떻게 유효화할지를 제어한다.
기본값은 `ONE_FULL_TEXT_SEARCH`이다. 이 때, `WHERE`구에 `MATCH AGAINST`가 1개만 있는 경우에만 컨디션 푸시 다운을 유효화한다.

이하는 유효한 값의 목록이다.
Value | Description
------|------------
NONE | 컨디션 푸시 다운을 사용하지 않는다.
ALL | 항상 컨디션 푸시 다운을 사용한다. 지금은 실험적인 기능이다.
ONE_FULL_TEXT_SEARCH | `WHERE`구 내에 `MATCH AGAINST`가 하나만 있는 경우에만 컨디션 푸시 다운을 유효화한다.<br> 이것이 기본 옵션이다.

```sql
mysql> SHOW VARIABLES LIKE 'mroonga_condition_push_down_type';
+----------------------------------+----------------------+
| Variable_name                    | Value                |
+----------------------------------+----------------------+
| mroonga_condition_push_down_type | ONE_FULL_TEXT_SEARCH |
+----------------------------------+----------------------+
1 row in set (0.00 sec)
```
