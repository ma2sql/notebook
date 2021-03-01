
mysql mysql_native_password 만들기 예제입니다.

```python
# ==== Python ====
# MySQL Password (Python)
import hashlib
def get_mysql_native_password(password):
    # https://blog.pythian.com/hashing-algorithm-in-mysql-password-2/
    return '*' + str.upper(
                     hashlib.sha1(
                         hashlib.sha1(
                             password.encode('utf-8')).digest()).hexdigest())


get_mysql_native_password('password')
'*2470C0C06DEE42FD1618BB99005ADCA2EC9D1E19'
```


```sql
==== MYSQL ====

select password('password');
+-------------------------------------------+
| password('password')                      |
+-------------------------------------------+
| *2470C0C06DEE42FD1618BB99005ADCA2EC9D1E19 |
+-------------------------------------------+


select sha1(unhex(sha1('password')));
+------------------------------------------+
| sha1(unhex(sha1('password')))            |
+------------------------------------------+
| 2470c0c06dee42fd1618bb99005adca2ec9d1e19 |
+------------------------------------------+
```