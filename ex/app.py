# 메인 Flask 앱 (중앙 허브)

from flask import Flask, render_template, request
from db import get_connection
from emotion import EmotionAnalyzer

app = Flask(__name__)

#URL 관리 , 폼데이터 받기, 모델 호출, 뷰 반환
@app.route("/diary", methods=["GET", "POST"])
def diary():   
    if request.method == "POST":
        user_id = request.form["user_id"]
        content = request.form["content"]
        diary_date = request.form["diary_date"]

        # 🔹 비즈니스 로직 호출
        analyzer = EmotionAnalyzer(content)
        analysis = analyzer.analyze()
        mood = analysis.get("mood", "")
        if "행복" in mood or "기쁨" in mood:
            emotion = "행복"
        elif "우울" in mood or "슬픔" in mood:
            emotion = "우울"
        elif "화" in mood or "분노" in mood:
            emotion = "분노"
        else:
            emotion = "보통"


        # 🔹 DB 저장
        conn = get_connection()
        cur = conn.cursor()
        sql = """
        INSERT INTO diaries (user_id, content, emotion, emotion_score, diary_date)
        VALUES (%s, %s, %s, %s, %s)
        """
        score_map = {"행복": 3, "보통": 2, "우울": 1, "분노": 0}
        cur.execute(sql, (user_id, content, emotion, score_map[emotion], diary_date))
        conn.commit()
        conn.close()

        return render_template("result.html", emotion=emotion)

    return render_template("diary.html")

if __name__ == "__main__":
    app.run(debug=True)


