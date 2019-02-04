# Echo Server

Redis의 이벤트 모델을 이해하기 위해, echodemo라는 예제를 직접 실행하여 본다.

[link to Redis 4.x Cookbook](https://subscription.packtpub.com/book/big_data_and_business_intelligence/9781783988167/1/ch01lvl1sec16/understanding-the-redis-event-model)


## create work directory
```
mkdir ~/coding
```

## cmake install
- download: https://cmake.org/download/
- install: https://cmake.org/install/
```bash
cd ~/coding
wget https://github.com/Kitware/CMake/releases/download/v3.13.3/cmake-3.13.3.tar.gz
tar xvfz cmake-3.13.3.tar.gz

# install cmake
# maybe, it needs c++11.
cd cmake-3.13.3
./bootstrap
make

# check version
~/coding/cmake-3.13.3/bin/cmake --version
...
cmake version 3.13.3

CMake suite maintained and supported by Kitware (kitware.com/cmake).
```

## download Redis & build dependecies
```bash
cd ~/coding
wget https://github.com/antirez/redis/archive/4.0.1.tar.gz
tar xvfz 4.0.1.tar.gz
 
# build dependecies
cd redis-4.0.1/deps
make lua linenoise hiredis
```

## download echodemo
```bash
cd ~/coding
git clone https://github.com/PacktPublishing/Redis-4.x-Cookbook.git

cd Redis-4.x-Cookbook/Chapter01/echodemo
cp -r echomemo ~/coding/redis-4.0.1/
cp src/release.sh ~/coding/redis-4.0.1/src/
```

## build echomemo
```bash
cd ~/coding/redis-4.0.1
~/coding/cmake-3.13.3/bin/cmake .
make
```

## Start echo-server !
```bash
~/coding/redis-4.0.1/echo-server
...
Server started at 0.0.0.0:8000!
```

## Send message to echo-server
```bash
nc 127.0.0.1 8000
...
Hello Client!
<Please input your message...>
```