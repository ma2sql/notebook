```python
from Crypto.Cipher import AES
from Crypto import Random
import binascii

# on the MySQL website: 
# "We chose 128 bits because it is much faster 
# and it is secure enough for most purposes."
# This means the final key must be 16 bytes.
_KEY_LEN = 16


def _pad(s):
    pad_value = _KEY_LEN - (len(val) % _KEY_LEN)
    return '{0}{1}'.format(val, chr(pad_value) * pad_value)


def _unpad(s):
    pad_value = ord(s[len(s)-1:])
    return s[:-pad_value]


def _mysql_aes_key(key):
    # Start with 16-byte block of null characters.
    final_key = bytearray(_KEY_LEN)
    # Iterate over all characters in our key.
    for i, c in enumerate(key):
        # ord: char to unicode int
        # chr: unicode int to char
        # ^=: XOR/ 
        final_key[i % _KEY_LEN] ^= ord(key[i])
    return bytes(final_key)


def mysql_aes_encrypt(val, key):
    k = _mysql_aes_key(key)
    v = _pad(val)

    cipher = AES.new(k, AES.MODE_ECB)

    return cipher.encrypt(v)


def mysql_aes_decrypt(val, key):
    k = _mysql_aes_key(key)
    cipher = AES.new(k, AES.MODE_ECB)
    _unpad = (lambda s: s[:-ord(s[len(s)-1:])])

    return unpad(cipher.decrypt(val)).decode()


def mysql_aes_encrypt_hex(val, key):
    return binascii.hexlify(mysql_aes_encrypt(val, key)).upper()


def mysql_aes_decrypt_hex(hex_val, key):
    val = hex_val.decode('hex')
    return mysql_aes_decrypt(val, key)
```