from datetime import timedelta
from bson import ObjectId
from flask import Flask, jsonify, request
from pymongo import MongoClient
import bcrypt
import redis
import random


redis = redis.Redis(
    host='redis_server',
    port='6379')

app = Flask(__name__)
client = MongoClient('mongodb://root:root@mongo_database_service:27017')





@app.route("/signup", methods=['POST'])
def signup():
    try:
        if request.method == 'POST':
            _data: dict = request.get_json()
            db = client.message_board
            users = db.users
            signup_user = users.find_one({'username': _data.get('username')})

            if signup_user:
                raise Exception("Username already exist")

            salt = bcrypt.gensalt(14).decode('utf-8')

            hashed = bcrypt.hashpw(_data.get('password').encode(
                'utf-8'), salt.encode('utf-8')).decode('utf-8')

            user = users.insert_one({'username': _data.get(
                'username'), 'password': hashed, 'salt': salt})

            response = jsonify(message="User signup succesful", request_state="success", _data={
                "user_id": str(user.inserted_id)
            })
            response.status_code = 201
            return response
        else:
            raise Exception("Method not allowded")
    except Exception as e:
        response = jsonify(message=str(e), request_status="error", data={})
        response.status_code = 500
        return response


@app.route('/signin', methods=['POST'])
def signin():
    try:
        if request.method == 'POST':
            _data: dict = request.get_json()
            db = client.message_board
            users = db.users
            signin_user = users.find_one(
                {'username': _data.get('username')})

            if not signin_user:
                raise Exception("User doesnot exist")

            if bcrypt.hashpw(_data.get('password').encode('utf-8'), signin_user.get('salt').encode('utf-8')) == signin_user['password'].encode('utf-8'):
                response = jsonify(message="User signin succesful", data={
                    'user_id': str(signin_user.get('_id'))}, request_state="success")
                _sessionId = '%032x' % random.randrange(16**32)
                redis.set(name=_sessionId, value=str(
                    signin_user.get('_id')), ex=timedelta(minutes=10))
                response.set_cookie(
                    'sessionId', value=_sessionId, httponly=True)
                response.status_code = 200
                return response
            else:
                raise Exception('Incorrect password')

        else:
            raise Exception("Method not allowded")
    except Exception as e:
        return jsonify(message=str(e), request_status="error", data={})


@app.route('/logout', methods=['GET'])
def logout():
    try:
        if request.method == 'GET':
            _sessionId = request.cookies.get('sessionId')
            
            if redis.get(_sessionId):
                redis.delete(_sessionId)
                response = jsonify(
                    message="User logout succesfully", request_status="success")
                response.status_code = 201
                return response
            else:
                raise Exception("User is not login")
        else:
            raise Exception("Method is not allowded")
    except Exception as e:
        return jsonify(message=str(e), request_status="error", data={"sessionid": _sessionId})


@app.route('/post_message', methods=['POST'])
def post_message():
    try:
        if request.method == 'POST':
            sessionId = request.cookies.get('sessionId')
            _userId = redis.get(sessionId).decode('utf-8')

            if not _userId:
                raise Exception("User is not login")

            _data: dict = request.get_json()
            db = client.message_board
            user_collection = db.users
            
            signin_user = user_collection.find_one({"_id":ObjectId(_userId)})

            if signin_user:
                message_collection = db.messages
                
                _inserted_data = message_collection.insert_one({
                    "message": _data.get("message"),
                    "user_id": signin_user.get("_id")
                })
                response = jsonify(
                    message="Message Submited succesfully", request_status="success", data= {
                        "message_id":  str(_inserted_data.inserted_id)
                    })
                response.status_code = 201
                return response
            else:
                raise Exception("User doesnot exist")

        else:
            raise Exception("Method is not allowded")
    except Exception as e:
        return jsonify(message=str(e), request_status="error", data={})


@app.route('/delete_message')
def delete_message():
    try:
        _sessionId = request.cookies.get('sessionId')
        _userId = redis.get(_sessionId).decode('utf-8')
        if not _userId:
            raise Exception("User is not login")
        db = client.message_board
        messages_collection = db.messages
        delete_obj = messages_collection.delete_one({"_id": ObjectId(request.args.get('message_id')), "user_id": ObjectId(_userId)})
        
        if not delete_obj:
            raise Exception("Unable to delete the message")
        response = jsonify(message="Message deleted succesfully", data={}, request_status="success")
        response.status_code = 200
        return response
    except Exception as e:
        return jsonify(message=str(e), request_status="error", data={})
    
    


@app.route('/list_all_message')
def list_all_message():
    try:
        _sessionId = request.cookies.get('sessionId')
        _userId = redis.get(_sessionId).decode('utf-8')
        if not _userId:
            raise Exception("User is not login")
        db = client.message_board
        messages_collection = db.messages
        _data = []
        for i in messages_collection.find({}):
            _data.append({
                "message": i.get("message"),
                "message_id": str(i.get("_id")),
                "user_id": str(i.get("user_id"))
            })
        response = jsonify(message="", request_status="success", data =_data)
        response.status_code = 200
        return response
    except Exception as e:
        return jsonify(message=str(e), request_status="error", data={})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)
