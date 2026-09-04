import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class TaxonomyLoader:
    def __init__(self, taxonomy_dir: str = None):
        if not taxonomy_dir:
            taxonomy_dir = str(Path(__file__).parent / "taxonomy")
        self.taxonomy_dir = Path(taxonomy_dir)
        self.cache: Dict[str, List[Dict[str, str]]] = {}
        
    def load_taxonomy(self, subject: str) -> List[Dict[str, str]]:
        """Load taxonomy for a given subject. Returns empty list if not found."""
        subject = subject.lower().strip()
        if subject in self.cache:
            return self.cache[subject]
            
        file_path = self.taxonomy_dir / f"{subject}.json"
        if not file_path.exists():
            logger.info(f"No taxonomy found for subject: {subject}")
            self.cache[subject] = []
            return []
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.cache[subject] = data.get("taxonomies", [])
            return self.cache[subject]
        except Exception as e:
            logger.error(f"Failed to load taxonomy {subject}.json: {e}")
            self.cache[subject] = []
            return []
            
    def is_valid_tag(self, subject: str, tag: str) -> bool:
        taxonomy = self.load_taxonomy(subject)
        for t in taxonomy:
            if t.get("tag") == tag:
                return True
        return False
