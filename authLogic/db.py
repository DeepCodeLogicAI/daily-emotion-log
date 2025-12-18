import pymysql

def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="1234",
        database="emotion_db",
        cursorclass=pymysql.cursors.DictCursor
    )