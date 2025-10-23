# envファイル読み込み用
from dotenv import load_dotenv
# .env を読み込み（開発時のみ）
load_dotenv()
from config import Config
# flask
from flask import Flask, request, render_template, jsonify
# flask_socketio WebSocket接続を行うのに使用
from flask_socketio import SocketIO, emit
# 異なるオリジン間のリクエストを許可するのに使用
from flask_cors import CORS
# 複数のスレッドを使用してPythonプログラムを並列実行するためのツール
import threading
# システムパッケージ
import os
# リクエスト
import requests
# 時間待機に使用
import time
# UUIDを使用
import uuid

# クライアントごとの識別情報を管理（session_id: WebSocketの接続）
clients = {}
# お客様のセッションIDとSlackチャンネルを管理する辞書
session_channels = {}
# **各セッションの最終アクティビティを記録**
session_activity = {}
# 各セッションの待機時間（秒）
SESSION_WAIT_TIME = 300

# webアプリ起動 
app = Flask(__name__)
app.config.from_object(Config)

# リアルタイム通信用ソケット定義
socketio = SocketIO(app, cors_allowed_origins="*")

# 決められたユーザーのSlackユーザーIDを設定
ADMIN_USERS = app.config['ADMIN_USERS']

# Slack APIヘッダー
SLACK_HEADERS = {
    "Authorization": f"Bearer {app.config['SLACK_BOT_TOKEN']}",
    "Content-Type": "application/json"
}

# ランダムなキーを生成
# reCAPTCHAのキーを設定
app.config['SECRET_KEY'] = os.urandom(24)  # セキュリティキー

CORS(app)

# appに対してのsoketIOを生成
socketio = SocketIO(app, cors_allowed_origins="*")

# root
@app.route('/', methods=["GET"])
def handle_root():
    return render_template('message.html')


# `/message` にアクセスしたときのみ WebSocket を有効化
@app.route("/message", methods=["GET"])
def message_page():
    return render_template("message.html", recaptcha_site_key=app.config['RECAPTCHA_PUBLIC_KEY'])

# クライアント接続時に `session_id` を生成して管理
@socketio.on("connect", namespace="/message")
def handle_connect():
    session_id = str(uuid.uuid4())  # ユニークIDを生成
    clients[session_id] = request.sid  # WebSocketのセッションIDを保存
    emit("session_id", session_id)  # クライアントに `session_id` を送信
    print(f"新しいクライアント接続: {session_id}")

#  """クライアントが切断したときの処理"""
@socketio.on("disconnect", namespace="/message")
def handle_disconnect():
    session_id = None
    # クライアントのセッションIDを探す
    for sid, client_sid in clients.items():
        if client_sid == request.sid:
            session_id = sid
            break
    if session_id:
        print(f"クライアント {session_id} が切断しました。セッションを削除します。")

        # **セッション情報を削除**
        if session_id in clients:
            del clients[session_id]
        if session_id in session_channels:
            del session_channels[session_id]
        if session_id in session_activity:
            del session_activity[session_id]

# **reCAPTCHAを検証してメッセージをSlackに送信**
@app.route("/send_message", methods=["POST"])
def send_message():
    data = request.json
    msg = data.get("message")
    session_id = data.get("session_id")
    recaptcha_response = data.get("g-recaptcha-response")
    if not session_id or not msg:
        return jsonify({"status": "error", "error": "セッションIDまたはメッセージが空です"}), 400
    # # **reCAPTCHA 検証**
    # if not recaptcha_response or not verify_recaptcha(recaptcha_response):
    #     return jsonify({"status": "error", "error": "reCAPTCHA の検証に失敗しました"}), 403
    print(f"Received message from {session_id}: {msg}")
    # Slackのチャンネルを取得 or 作成
    channel_id = get_or_create_slack_channel(session_id)
    
    if channel_id:
        slack_data = {
            "channel": channel_id,
            "text": f"ユーザーのメッセージ: {msg}",
            "username": "ChatBot"
        }
        response = requests.post("https://slack.com/api/chat.postMessage", headers=SLACK_HEADERS, json=slack_data)

        if response.status_code == 200 and response.json().get("ok"):
            print(f"Slackにメッセージ送信成功: {msg}")
            session_activity[session_id] = time.time()
            return jsonify({"status": "ok"})
        else:
            print(f"Slackメッセージ送信エラー: {response.json()}")
            return jsonify({"status": "error", "error": "Slackメッセージ送信に失敗しました"}), 500
    return jsonify({"status": "error", "error": "Slackチャンネルが取得できませんでした"}), 500


# クライアントとリアルタイム通信 (namespace `/message`)
@socketio.on("message", namespace="/message")
def handle_message(data):
    msg = data.get("msg")
    session_id = data.get("session_id")
    if not session_id:
        print("エラー: session_id が None")
        return
    # **セッションが途絶えたメッセージを受け取ったら削除**
    if "セッションが途絶えました" in msg:
        print(f"セッション {session_id} が終了しました。セッションデータを削除します。")
        if session_id in clients:
            del clients[session_id]
        if session_id in session_channels:
            del session_channels[session_id]
        if session_id in session_activity:
            del session_activity[session_id]
        return
    # Slackのチャンネルを取得 or 作成
    channel_id = get_or_create_slack_channel(session_id)
    if channel_id:
        slack_data = {
            "channel": channel_id,
            "text": f"ユーザーのメッセージ: {msg}",
            "username": "ChatBot"
        }
        response = requests.post("https://slack.com/api/chat.postMessage", headers=SLACK_HEADERS, json=slack_data)

        if response.status_code == 200 and response.json().get("ok"):
            print(f"Slackにメッセージ送信成功: {msg}")
            session_activity[session_id] = time.time()
        else:
            print(f"Slackメッセージ送信エラー: {response.json()}")


@app.route("/slack", methods=["POST"])
def slack_webhook():
    data = request.json
    # Slack の URL 検証リクエストに対応
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data.get("challenge")})
    event = data.get("event", {})
    text = event.get("text", "")
    user_id = event.get("user", "")
    channel_id = event.get("channel", "")
    subtype = event.get("subtype", "")
    # **システム通知を除外（subtype がある場合はシステムメッセージ）**
    if subtype or not user_id:
        print(f"システムメッセージを除外: {text}")  # デバッグログ
        return jsonify({"status": "ignored"}), 200
    # **指定されたユーザー (`ADMIN_USERS`) のみメッセージを送信**
    if user_id not in ADMIN_USERS:
        print(f"許可されていないユーザー {user_id} のメッセージを無視: {text}")  # デバッグログ
        return jsonify({"status": "ignored"}), 200
    # session_id を検索
    session_id = None
    for key, value in session_channels.items():
        if value == channel_id:
            session_id = key
            break
    # **クライアントにメッセージを送信**
    if session_id and session_id in clients:
        socketio.emit("message", text, room=clients[session_id], namespace="/message")
    return jsonify({"status": "ok"}), 200


# **Slackのチャンネルを作成または取得**
def get_or_create_slack_channel(session_id):
    if session_id in session_channels:
        return session_channels[session_id]
    channel_name = f"{app.config['SLACK_CHANNEL_PREFIX']}{session_id}"
    # **既存のチャンネルを検索**
    list_url = "https://slack.com/api/conversations.list"
    response = requests.get(list_url, headers=SLACK_HEADERS)
    if response.status_code == 200:
        channels = response.json().get("channels", [])
        for channel in channels:
            if channel["name"] == channel_name:
                session_channels[session_id] = channel["id"]
                return channel["id"]
    # **新規チャンネルを作成**
    create_url = "https://slack.com/api/conversations.create"
    data = {"name": channel_name}
    response = requests.post(create_url, headers=SLACK_HEADERS, json=data)
    if response.status_code == 200 and response.json().get("ok"):
        channel_id = response.json()["channel"]["id"]
        session_channels[session_id] = channel_id
        invite_users_to_channel(channel_id, ADMIN_USERS)
        return channel_id
    return None

# **指定ユーザーをチャンネルに招待**
def invite_users_to_channel(channel_id, users):
    invite_url = "https://slack.com/api/conversations.invite"
    data = {"channel": channel_id, "users": ",".join(users)}
    response = requests.post(invite_url, headers=SLACK_HEADERS, json=data)
    if response.status_code == 200 and response.json().get("ok"):
        print(f"指定ユーザーをチャンネルに招待: {users}")

# **SESSION_WAIT_TIME分間アクティビティがないセッションを終了する関数**
def check_inactive_sessions():
    current_time = time.time()
    inactive_sessions = []
    for session_id, last_time in session_activity.items():
        if current_time - last_time > SESSION_WAIT_TIME:  # セッションが一定時間アクティブでない場合
            channel_id = session_channels.get(session_id)
            if channel_id:
                print(f"セッション {session_id} が {SESSION_WAIT_TIME} 秒間アクティビティなし。終了処理を実行。")
                # **管理者 (`ADMIN_USERS`) をチャンネルから削除**
                remove_admin_users_from_channel(channel_id)
                # **Slackに「セッション終了」メッセージを投稿**
                message = f"{SESSION_WAIT_TIME}秒間通信がなかったため、セッションが終了しました。"
                slack_data = {"channel": channel_id, "text": message}
                requests.post("https://slack.com/api/chat.postMessage", headers=SLACK_HEADERS, json=slack_data)
                # **ボットをチャンネルから退出**
                requests.post("https://slack.com/api/conversations.leave", headers=SLACK_HEADERS, json={"channel": channel_id})
                # **チャンネルをアーカイブ**
                requests.post("https://slack.com/api/conversations.archive", headers=SLACK_HEADERS, json={"channel": channel_id})
                # **Webクライアントにもセッション終了を通知**
                if session_id in clients:
                    socketio.emit("message", message, room=clients[session_id], namespace="/message")
                inactive_sessions.append(session_id)
    # **終了したセッションを削除**
    for session_id in inactive_sessions:
        del session_activity[session_id]
        del session_channels[session_id]
        if session_id in clients:
            del clients[session_id]
    # **継続的に実行するためのタイマー**
    threading.Timer(SESSION_WAIT_TIME, check_inactive_sessions).start()


# **ADMIN_USERS のみをチャンネルから削除する関数**
def remove_admin_users_from_channel(channel_id):
    # **チャンネルのメンバーを取得**
    members_url = "https://slack.com/api/conversations.members"
    response = requests.get(members_url, headers=SLACK_HEADERS, params={"channel": channel_id})
    if response.status_code == 200:
        resp_json = response.json()
        if resp_json.get("ok"):
            members = resp_json["members"]
            print(f"チャンネル {channel_id} のメンバー一覧: {members}")
            # **ADMIN_USERS のみを強制退出**
            for user_id in ADMIN_USERS:
                if user_id in members:
                    kick_url = "https://slack.com/api/conversations.kick"
                    kick_data = {"channel": channel_id, "user": user_id}
                    kick_response = requests.post(kick_url, headers=SLACK_HEADERS, json=kick_data)
                    if kick_response.status_code == 200 and kick_response.json().get("ok"):
                        print(f"管理者 {user_id} をチャンネル {channel_id} から削除しました。")
                    else:
                        print(f"管理者削除エラー: {kick_response.json()}")
        else:
            print(f"メンバー取得エラー: {resp_json}")
    else:
        print(f"メンバー取得HTTPエラー: {response.json()}")

# Google reCAPTCHAの検証を行う関数
def verify_recaptcha(recaptcha_response):
    """Google reCAPTCHAの検証を行う関数"""
    url = 'https://www.google.com/recaptcha/api/siteverify'
    data = {
        'secret': app.config['RECAPTCHA_PRIVATE_KEY'],
        'response': recaptcha_response
    }
    r = requests.post(url, data=data)
    result = r.json()
    return result.get('success', False)

# メイン
if __name__ == '__main__':
    socketio.run(app, host="127.0.0.1", port=5001)