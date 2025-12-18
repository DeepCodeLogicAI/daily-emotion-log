import pymysql

def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="dabin1224",
        database="emotion_db",
        cursorclass=pymysql.cursors.DictCursor
    )