from __future__ import print_function
import string
import random

chars = string.ascii_lowercase + string.ascii_uppercase + string.digits

def get_password(password_length=10):
    return ''.join([random.choice(chars) for _ in range(password_length)])


print(get_password())