"""Base class for parsing CSV/XLS/XLSX dataframes."""
import pandas as pd
from abc import abstractmethod
from typing import List, Dict, Any
from ..utils import detect_encoding
from .base import BaseParser


class DataFrameParser(BaseParser):
    def can_parse(self, file_path: str) -> bool:
        low = file_path.lower()
        return low.endswith((".csv", ".tsv", ".xlsx", ".xls"))

    def read_dataframe(self, file_path: str) -> pd.DataFrame:
        low = file_path.lower()
        if low.endswith('.csv'):
            return pd.read_csv(file_path, encoding=detect_encoding(file_path))
        if low.endswith('.tsv'):
            return pd.read_csv(file_path, sep='\t', encoding=detect_encoding(file_path))
        # let pandas choose engine; works for xls/xlsx if deps installed
        return pd.read_excel(file_path)

    def parse(self, file_path: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        log = context.get('log')
        try:
            df = self.read_dataframe(file_path)
        except Exception as e:
            if log:
                log(f"Failed to read table {file_path}: {e}")
            return []
        return self.parse_dataframe(file_path, df, context)

    @abstractmethod
    def parse_dataframe(self, path_hint: str, df: pd.DataFrame, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        raise NotImplementedError
