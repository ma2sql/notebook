
---
tags: [docker, redis]
---

redis 이미지 받아오기
```
docker pull redis:latest
```

container 실행
```
docker run --name some-redis -d -p 6379:6379 redis
```

redis-cli를 이용한 접근
```
docker run -it --network host --rm redis redis-cli
```