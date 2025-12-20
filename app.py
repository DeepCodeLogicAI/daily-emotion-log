import os
import sys

print("=" * 50)
print("현재 실행 경로:", os.getcwd())
print("실행 중인 파일:", __file__)
print("Python 실행 파일:", sys.executable)
print("=" * 50)

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
from db import get_connection
from emotion import EmotionAnalyzer
import atexit

# 어떤 파일들이 로드되었는지 확인
print(f"db 모듈 위치: {get_connection.__module__}")
print(f"EmotionAnalyzer 모듈 위치: {EmotionAnalyzer.__module__}")

app = Flask(__name__)   # Flask 앱 초기화
app.secret_key = 'your-secret-key-change-this-in-production'  # 세션을 위한 시크릿 키
# atexit.register(get_connection.close)

# 사용자 테이블 생성 함수
def init_users_table():
    """users 테이블이 없으면 생성"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    except Exception as e:
        print(f"테이블 생성 오류: {e}")
    finally:
        conn.close()

# 앱 시작 시 테이블 초기화
init_users_table()

# 메인 화면 - 로그인/회원가입 선택
@app.route("/")
def index():
    return render_template("index.html")

# 로그인
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if not username or not password:
            flash("아이디와 비밀번호를 입력해주세요.")
            return render_template("login.html")
        
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, username, password FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                # flash("로그인 성공!")
                return redirect(url_for("diary_list"))
            else:
                flash("아이디 또는 비밀번호가 올바르지 않습니다.")
        except Exception as e:
            print(f"로그인 오류: {e}")
            flash("로그인 중 오류가 발생했습니다.")
        finally:
            conn.close()
    
    return render_template("login.html")

# 회원가입
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if not username or not password:
            flash("아이디와 비밀번호를 입력해주세요.")
            return render_template("register.html")
        
        if len(username) < 3:
            flash("아이디는 3자 이상이어야 합니다.")
            return render_template("register.html")
        
        if len(password) < 4:
            flash("비밀번호는 4자 이상이어야 합니다.")
            return render_template("register.html")
        
        conn = get_connection()
        cur = conn.cursor()
        try:
            # 중복 체크
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                flash("이미 존재하는 아이디입니다.")
                return render_template("register.html")
            
            # 비밀번호 해싱 후 저장
            hashed_password = generate_password_hash(password)
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", 
                       (username, hashed_password))
            conn.commit()
            flash("회원가입이 완료되었습니다. 로그인해주세요.")
            return redirect(url_for("login"))
        except Exception as e:
            print(f"회원가입 오류: {e}")
            flash("회원가입 중 오류가 발생했습니다.")
        finally:
            conn.close()
    
    return render_template("register.html")

# 로그아웃
@app.route("/logout")
def logout():
    session.clear()
    # flash("로그아웃되었습니다.")
    return redirect(url_for("index"))

# 일기 목록 보기
@app.route("/diary/list")
def diary_list():
    if 'user_id' not in session:
        flash("로그인이 필요합니다.")
        return redirect(url_for("login"))
    
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, content, emotion, emotion_score, diary_date, analysis
            FROM diaries 
            WHERE user_id = %s 
            ORDER BY diary_date DESC
        """, (session['user_id'],))
        diaries = cur.fetchall()
        
        # analysis JSON 문자열을 파싱
        for diary in diaries:
            if diary.get('analysis'):
                try:
                    parsed = json.loads(diary['analysis'])
                    # 기존 형식(psychologicalState 등)과 새 형식(summary) 호환
                    if 'summary' not in parsed and 'psychologicalState' in parsed:
                        # 기존 형식을 새 형식으로 변환
                        parsed['summary'] = parsed.get('advice', parsed.get('psychologicalState', '분석 결과'))
                    diary['analysis'] = parsed
                except:
                    diary['analysis'] = None
        
        # 최근 5일의 emotion_score 데이터 가져오기
        cur.execute("""
            SELECT diary_date, emotion_score, emotion
            FROM diaries 
            WHERE user_id = %s 
            ORDER BY diary_date DESC
            LIMIT 5
        """, (session['user_id'],))
        recent_scores = cur.fetchall()
        
        # 날짜 순서대로 정렬 (오래된 것부터)
        recent_scores = sorted(recent_scores, key=lambda x: x['diary_date'])
        
    except Exception as e:
        print(f"일기 목록 조회 오류: {e}")
        diaries = []
        recent_scores = []
    finally:
        conn.close()
    
    return render_template("diary_list.html", diaries=diaries, recent_scores=recent_scores, user={'username': session.get('username')})

# 일기 작성 및 AI 분석
@app.route("/diary", methods=["GET", "POST"])
def diary():   
    # 로그인 체크
    if 'user_id' not in session:
        flash("로그인이 필요합니다.")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        user_id = session['user_id']
        content = request.form.get("content")
        diary_date = request.form.get("diary_date")

        if not content or not diary_date:
            flash("날짜와 내용을 모두 입력해주세요.")
            return render_template("diary.html", user={'username': session.get('username')}, today=datetime.now().strftime('%Y-%m-%d'))

        # 🔹 AI 분석 로직 호출
        analysis_result = None
        emotion = "보통"
        
        try:
            print("AI 분석 시작...")
            analyzer = EmotionAnalyzer(content)
            analysis_result = analyzer.analyze()
            print(f"AI 분석 결과: {analysis_result}")
            
            # 감정 분류 (Happy, Neutral, Sad, Angry -> 한국어로 변환)
            mood = analysis_result.get("mood", "Neutral").strip() if analysis_result else "Neutral"
            mood_lower = mood.lower()
            
            if mood_lower == "happy":
                emotion = "행복"
            elif mood_lower == "sad":
                emotion = "우울"
            elif mood_lower == "angry":
                emotion = "분노"
            else:  # Neutral 또는 기타
                emotion = "보통"
            
            print(f"분류된 감정: {emotion} (원본: {mood})")
            
        except Exception as ai_error:
            print(f"AI 분석 오류: {ai_error}")
            import traceback
            traceback.print_exc()
            # AI 분석 실패 시 기본값 사용
            analysis_result = {
                "mood": "Neutral",
                "summary": "분석 중 오류가 발생했습니다."
            }
            emotion = "보통"
            flash("AI 분석 중 오류가 발생했지만 일기는 저장되었습니다.")

        # 🔹 DB 저장 (분석 결과도 함께 저장)
        conn = get_connection()
        cur = conn.cursor()
        has_analysis = False
        try:
            # diaries 테이블에 analysis 컬럼이 있는지 확인하고 없으면 추가
            try:
                cur.execute("SHOW COLUMNS FROM diaries LIKE 'analysis'")
                has_analysis = cur.fetchone() is not None
                if not has_analysis:
                    cur.execute("ALTER TABLE diaries ADD COLUMN analysis TEXT")
                    conn.commit()
                    has_analysis = True
            except Exception as col_error:
                print(f"컬럼 확인/추가 오류: {col_error}")
                # 컬럼 추가 실패해도 계속 진행 (analysis 없이 저장)
            
            # 분석 결과를 JSON 문자열로 저장 (analysis_result가 None이 아닐 때만)
            analysis_json = None
            if analysis_result:
                try:
                    analysis_json = json.dumps(analysis_result, ensure_ascii=False)
                except Exception as json_error:
                    print(f"JSON 변환 오류: {json_error}")
                    analysis_json = None
            
            score_map = {"행복": 3, "보통": 2, "우울": 1, "분노": 0}
            
            # 같은 날짜의 일기가 있는지 확인 (UNIQUE 제약 처리)
            cur.execute("SELECT id FROM diaries WHERE user_id = %s AND diary_date = %s", 
                       (user_id, diary_date))
            existing = cur.fetchone()
            
            if existing:
                # 기존 일기 업데이트
                if has_analysis and analysis_json:
                    sql = """
                    UPDATE diaries 
                    SET content = %s, emotion = %s, emotion_score = %s, analysis = %s
                    WHERE id = %s
                    """
                    cur.execute(sql, (content, emotion, score_map[emotion], analysis_json, existing['id']))
                else:
                    sql = """
                    UPDATE diaries 
                    SET content = %s, emotion = %s, emotion_score = %s
                    WHERE id = %s
                    """
                    cur.execute(sql, (content, emotion, score_map[emotion], existing['id']))
                flash("해당 날짜의 일기가 이미 존재하여 업데이트되었습니다.")
            else:
                # 새 일기 삽입
                if has_analysis and analysis_json:
                    sql = """
                    INSERT INTO diaries (user_id, content, emotion, emotion_score, diary_date, analysis)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cur.execute(sql, (user_id, content, emotion, score_map[emotion], diary_date, analysis_json))
                else:
                    sql = """
                    INSERT INTO diaries (user_id, content, emotion, emotion_score, diary_date)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    cur.execute(sql, (user_id, content, emotion, score_map[emotion], diary_date))
            
            conn.commit()
            print(f"일기 저장 성공: user_id={user_id}, date={diary_date}, emotion={emotion}")
        except Exception as e:
            print(f"일기 저장 오류: {e}")
            import traceback
            traceback.print_exc()
            flash(f"일기 저장 중 오류가 발생했습니다: {str(e)}")
            try:
                conn.rollback()
            except:
                pass
            return render_template("diary.html", user={'username': session.get('username')}, today=datetime.now().strftime('%Y-%m-%d'))
        finally:
            conn.close()

        # 분석 결과 페이지로 이동
        # analysis_result가 None이면 기본값 사용
        if not analysis_result:
            analysis_result = {
                "psychologicalState": "분석 결과를 불러올 수 없습니다.",
                "mood": emotion,
                "reason": "일기는 저장되었지만 분석 결과를 표시할 수 없습니다.",
                "advice": "일기는 정상적으로 저장되었습니다."
            }
        
        return render_template("result.html", 
                             emotion=emotion,
                             analysis=analysis_result,
                             diary_date=diary_date,
                             user={'username': session.get('username')})

    # 오늘 날짜를 기본값으로 설정
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template("diary.html", user={'username': session.get('username')}, today=today)

if __name__ == "__main__":
    app.run(debug=True)


