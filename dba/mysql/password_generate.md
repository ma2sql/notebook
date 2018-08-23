## Python에서 mysql_native_password 해시값 만들기
때때로 MySQL에서 사용되는 패스워드 해시값이 필요할 때가 있다. (신규 계정 생성이라던지..)
이때, mysql에 접속하여 Query를 작성하지 않고도, 패스워드 해시값을 만들 수 있는 방법이 있다.

### Python
- ref: https://blog.pythian.com/hashing-algorithm-in-mysql-password-2/
```python
# MySQL Password (Python)
def get_mysql_native_password(password):
    return '*' + str.upper(
                     hashlib.sha1(
                         hashlib.sha1(
                             password.encode('utf-8')).digest()).hexdigest())


>>> get_mysql_native_password('password')
'*2470C0C06DEE42FD1618BB99005ADCA2EC9D1E19'
```


### MySQL
```sql
select password('password');
+-------------------------------------------+
| password('password')                      |
+-------------------------------------------+
| *2470C0C06DEE42FD1618BB99005ADCA2EC9D1E19 |
+-------------------------------------------+


select sha1(unhex(sha1('password')));
+------------------------------------------+
| sha1(unhex(sha1('password')))            |
+------------------------------------------+
| 2470c0c06dee42fd1618bb99005adca2ec9d1e19 |
+------------------------------------------+
```
