import pymysql

def get_connection():
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="123456",
        database="emotion_db",
        cursorclass=pymysql.cursors.DictCursor
    )
    print(" 데이터베이스 연결 성공!")
    return conn
