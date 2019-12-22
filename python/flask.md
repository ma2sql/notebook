## Install

```
pip install -U flask
pip install -U Flask-SQLAlchemy
```

```python
from flask import Flask, jsonify
import celery

c = celery.Celery('tasks',
                  broker="__BROKER_URL__",
                  backend="__BACKEND_URL__")

app = Flask(__name__)

@app.route('/user', methods=['GET'])
def get_user():
    tasks = celery.group([c.signature('tasks.add', args=(i,i)) for i in range(2)])()
    try:
        val = tasks.get()
    # TODO: Give proper error
    except BaseException as e:
        val = None
    return jsonify({'val': val}), 200

if __name__ == '__main__':
    app.run(debug=True)
```