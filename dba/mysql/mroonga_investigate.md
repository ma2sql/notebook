# Groonga & Mroonga 연구

### Lock Free?
- 기본적으로 Lock Free라는 것을 말하는 공식 메뉴얼
  - http://groonga.org/ja/docs/characteristic.html#sharable-storage-and-read-lock-free
- Mroonga는 스토리지 엔진 레벨에서 Lock을 사용하지 않는다.
- Groonga Level에서 파일 단위의 락을 사용한다.
  - https://www.slideshare.net/yoku0825/how-to-backup-your-mroonga-database
- 그래서 MySQL+Mroonga조합에서 장애가 발생할 때, Groonga에서는 별도의 락 해제 조치가 없는 경우가 생길 수 있고, 이로 인해 MySQL재기동 이후에도 락이 유지되는 일이 발생할 수 있음
  - http://y-ken.hatenablog.com/entry/how-to-unlock-mroonga-database
```
use my_db;
select mroonga_command('clearlock');
flush tables;
```
