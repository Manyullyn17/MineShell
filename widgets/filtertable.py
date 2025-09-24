from copy import deepcopy
from rich.text import TextType
from helpers import CustomTable
from typing import Any, Optional

class FilterTable(CustomTable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._master_data: dict[Any, dict[Any, Any]] = {}  # copy of self._data

    def add_row(
        self,
        *cells,
        height: int | None = 1,
        key: str | None = None,
        label: TextType | None = None,
    ):
        # Call base method to preserve all functionality
        row_key = super().add_row(*cells, height=height, key=key, label=label)
        # Store a copy in master data
        self._master_data[row_key] = deepcopy(self._data[row_key])
        return row_key

    def filter_rows(self, filters: dict[str, list], search_term: Optional[str] = None, search_columns: Optional[list[str]] = None):
        """Rebuild table based on a filter function applied to master rows."""
        """
        Filters the table based on a dict of column -> allowed values (OR within column, AND across columns)
        Optionally filters by a search term across specified columns.
        """
        def row_passes(row: dict[str, Any]) -> bool:
            # Column filters
            for col, allowed_values in filters.items():
                if allowed_values and row.get(col) not in allowed_values:
                    return False
            # Search term filter
            if search_term and search_columns:
                if not any(search_term.lower() in str(row.get(col, "")).lower() for col in search_columns):
                    return False
            return True

        self.clear()  # clear current rows but keep columns
        for row_key, row_data in self._master_data.items():
            if row_passes(row_data):
                super().add_row(*[row_data[col.key] for col in self.ordered_columns], key=row_key)

