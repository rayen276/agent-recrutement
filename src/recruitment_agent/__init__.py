"""Agent RH : analyse de CV, comparaison à une offre et lettre de motivation."""

from .agent import RecruitmentAgent
from .models import Analysis, LetterOptions, Result

__all__ = ["RecruitmentAgent", "Analysis", "LetterOptions", "Result"]
__version__ = "1.0.0"
