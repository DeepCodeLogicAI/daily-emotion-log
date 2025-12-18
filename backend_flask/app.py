# app.py
import os
import traceback
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy.orm import Session
from pydantic import ValidationError

from db import engine, SessionLocal, Base
from models import DiaryEntry
from schemas import DiaryEntryIn, AnalysisResult
from gemini_client import analyze as gemini_analyze

print(">>> RUNNING FILE:", os.path.abspath(__file__))

# DB 테이블 생성
Base.metadata.create_all(bind=engine)

# ✅ 프론트(static)까지 같이 서빙
# - static_folder: frontend 폴더
# - static_url_path: ""  => / 로 정적 접근 가능(단, 우리는 "/"는 index로 직접 라우팅)
app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)

# -----------------------------
# API ROUTES (정적 라우트보다 위)
# -----------------------------
@app.get("/health")
def health():
    return jsonify({"ok": True})

@app.post("/analyze")
def analyze_and_store():
    db: Session = SessionLocal()
    try:
        payload = request.get_json(force=True) or {}
        entry = DiaryEntryIn.model_validate(payload)

        # Gemini 분석
        analysis_dict = gemini_analyze(entry)
        analysis = AnalysisResult.model_validate(analysis_dict)

        # DB 저장
        row = DiaryEntry(
            date=entry.date,
            diaryText=entry.diaryText,
            selfReportedMood=entry.selfReportedMood,
            analysis=analysis.model_dump(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)

        return jsonify({
            "id": row.id,
            "date": row.date,
            "diaryText": row.diaryText,
            "selfReportedMood": row.selfReportedMood,
            "analysis": row.analysis
        })

    except ValidationError as e:
        db.rollback()
        return jsonify({"error": "유효성 검사 오류", "detail": e.errors()}), 400

    except RuntimeError as e:
        db.rollback()
        return jsonify({"error": "런타임 오류", "detail": str(e)}), 500

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return jsonify({"error": "서버 오류", "detail": str(e)}), 500

    finally:
        db.close()

@app.get("/entries")
def entries():
    limit = int(request.args.get("limit", 20))
    db: Session = SessionLocal()
    try:
        rows = db.query(DiaryEntry).order_by(DiaryEntry.id.desc()).limit(limit).all()
        return jsonify([
            {
                "id": r.id,
                "date": r.date,
                "diaryText": r.diaryText,
                "selfReportedMood": r.selfReportedMood,
                "analysis": r.analysis
            }
            for r in rows
        ])
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "서버 오류", "detail": str(e)}), 500
    finally:
        db.close()

# -----------------------------
# FRONTEND ROUTES
# -----------------------------
@app.get("/")
def serve_index():
    # frontend/index.html 서빙
    return send_from_directory("frontend", "index.html")

@app.get("/<path:path>")
def serve_frontend_files(path):
    """
    frontend 폴더 안 파일을 서빙.
    - 단, /health /analyze /entries 같은 API 경로는 위에서 먼저 매칭되므로 여기로 오지 않음.
    """
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    file_path = os.path.join(frontend_dir, path)

    if os.path.isfile(file_path):
        return send_from_directory("frontend", path)

    # SPA처럼 동작시키고 싶으면(라우터 쓸 때) index.html로 fallback 가능
    # 지금은 단일 페이지라서 파일이 없으면 404 반환
    return jsonify({"error": "Not found"}), 404


# -----------------------------
# ERROR HANDLERS
# -----------------------------
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    # ✅ 기존에 5002를 쓰고 있었다면 그대로 유지
    port = int(os.getenv("PORT", "5002"))
    print(f">>> Starting Flask server on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=True, use_reloader=False)
