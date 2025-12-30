from Crypto.Cipher import AES
import base64
import hashlib

KEY = hashlib.sha256(b"XXXXXXXXX").digest()
IV = b"\xXX" * 16

def encrypt(plaintext):
    cipher = AES.new(KEY, AES.MODE_CFB, IV)
    return base64.b64encode(cipher.encrypt(plaintext.encode())).decode()

def decrypt(ciphertext):
    cipher = AES.new(KEY, AES.MODE_CFB, IV)
    return cipher.decrypt(base64.b64decode(ciphertext)).decode()
