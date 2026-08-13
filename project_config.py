"""Repository-wide artifact locations shared across system modules."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CARDS_JSON = DATA_DIR / "cards.json"
CARD_CHECKPOINT_JSON = DATA_DIR / "cards.checkpoint.json"
FAILED_CARD_URLS_JSON = DATA_DIR / "failed_urls.json"
TOURNAMENTS_DIR = DATA_DIR / "tournaments"
TOURNAMENT_DATASET_JSON = TOURNAMENTS_DIR / "dataset.json"
ANALYSIS_JSON = DATA_DIR / "analysis.json"
MODEL_PATH = DATA_DIR / "model.joblib"
