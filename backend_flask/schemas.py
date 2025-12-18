from typing import List, Optional, Literal
from pydantic import BaseModel, Field

EmotionLabel = Literal[
    "기쁨","슬픔","분노","불안","두려움","혐오","놀람","평온",
    "피로","외로움","죄책감","무기력","만족","답답함"
]

class DiaryEntryIn(BaseModel):
    diaryText: str = Field(..., min_length=1, max_length=5000)
    date: str = Field(..., description="YYYY-MM-DD")
    selfReportedMood: Optional[str] = None

class EmotionItem(BaseModel):
    label: EmotionLabel
    confidence: float = Field(..., ge=0.0, le=1.0)

class RiskFlag(BaseModel):
    level: Literal["low","medium","high"]
    message: str

class AnalysisResult(BaseModel):
    PrimaryEmotion: EmotionItem
    SecondaryEmotions: List[EmotionItem] = []
    Valence: float = Field(..., ge=-1.0, le=1.0)
    Arousal: float = Field(..., ge=0.0, le=1.0)
    Intensity: int = Field(..., ge=0, le=100)
    Summary: str
    Rationale: List[str] = []
    Suggestions: List[str] = []
    RiskFlag: Optional[RiskFlag] = None