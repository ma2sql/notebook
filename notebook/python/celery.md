### Avoid launching synchronous subtasks
http://docs.celeryq.org/en/latest/userguide/tasks.html#task-synchronous-subtasks

Celery에서 호출된 task내의 작업에 대해서는 get() 메서드를 호출 할 수가 없다.
@app.task로 표시된 메서드에 대해서는 일괄적으로 비동기 처리를 하는 것 같다.
즉, task내에서 chord를 호출하게되면, 각각의 결과를 일괄적으로 정리하여 get()을 호출하여 받아볼 수는 없으며, callback등을 이용해야만 한다.
방법이 없을까...

Test의 흐름
http://docs.celeryproject.org/en/latest/getting-started/first-steps-with-celery.html
**redis 설치**
```
# redis daemon
docker run -d --name redis -p 6379:6379 redis:4.0

# access
docker exec -it __CONTAINER__ /bin/bash
```

**celery 데몬 띄우기**
```
celery -A tasks worker --loglevel=info
```
celery가 @app.task 데코레이터된 메서드를 자동적으로 태스크로 인식하여,
기동 시점에 등록하는 듯?
간단한 연습용이므로 여기에 메서드를 등록해서 다른 곳에서 불러 쓰면 될 것 같다.
```
import os
from celery import Celery

import time
import random

app = Celery('tasks', broker='redis://:@127.0.0.1:6379/0', backend='redis://:@127.0.0.1:6379/0')

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
```

**테스트 코드**
```
import os
from celery import Celery
from celery import chain, group, chord

import time
import random

app = Celery('tasks', broker='redis://127.0.0.1:6379/0', backend='redis://127.0.0.1:6379/0')

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

@app.task
def test0():
    return random.randint(5, 10)

@app.task
def test1(a):
    sleep_time = random.uniform(0,3)
    time.sleep(sleep_time)
    return a

@app.task
def callback(r,a,b):
    print(r,a,b)
    return (sum(r), sum(r)/len(r))

@app.task
def task_case1():
    print('start!')
    chord_result = chord(test1.s(i) for i in range(10))(callback.s(a=1,b=2))
    print('end!')

@app.task
def task_case2():
    print('start!')
    chord_result = chord(test1.s(i) for i in range(10))(callback.s(a=1,b=2))
    # Error! RuntimeError(u'Never call result.get() within a task!...')
    a = chord_result.get()
    print('end!')

def main():
    task_case1.delay()
    task_case2.delay()
```


http://docs.celeryq.org/en/latest/userguide/tasks.html#task-synchronous-subtasks
task내에서 다시 task를 호출하게되면, get()을 이용하여 task를 동기화하고 값을 가져오는 것은 좋지 않다. 비효율적이기도 하고 데드락이 발생할 수도 있기 때문이다. 이러한 경우 그냥 callback을 이용해야할 것 같다.
