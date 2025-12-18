from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.types import JSON
from db import Base

class DiaryEntry(Base):
    __tablename__ = "diary_entries"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=False)
    diaryText = Column(Text, nullable=False)
    selfReportedMood = Column(String, nullable=True)

    analysis = Column(JSON, nullable=False)  # 분석 결과 통째 저장