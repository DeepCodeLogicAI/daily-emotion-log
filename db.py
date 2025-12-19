import pymysql
from pymysql import Error
import os
from dotenv import load_dotenv

# .env 파일에 정의된 환경 변수를 로드
load_dotenv()

def get_connection():
    
    conn = pymysql.connect(
        host=os.getenv("DB_HOST"),        # DB 주소
        user=os.getenv("DB_USER"),        # DB 사용자명
        password=os.getenv("DB_PASSWORD"),# DB 비밀번호 (노출 X)
        database=os.getenv("DB_NAME"),    # DB 이름
        cursorclass=pymysql.cursors.DictCursor
    )
    
    print(" 데이터베이스 연결 성공!")
    return conn
