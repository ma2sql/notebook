# docker-compose 로 Redis 설치하기

## 0. 테스트 디렉터리 생성
```bash
mkdir __MY_DOCKER_HOME__
cd __MY_DOCKER_HOME__
```

## 1. Dockerfile 의 작성
*대소문자 주의!*: **Dockerfile** 
```
FROM redis:4.0

CMD ["redis-server"]
```

## 2. docker image build
```bash
docker image build -t mymy/test-redis:latest .
```

## 3. docker container run
```bash
docker container run -d -p 7000:6379 mymy/test-redis:latest 
```

## 4. docker-compose