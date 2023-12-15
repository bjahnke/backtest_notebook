import pandas as pd
from pandas.api.extensions import register_dataframe_accessor

class BaseTableAccessor:
    required_columns = set()

    def __init__(self, pandas_obj):
        self._validate(pandas_obj)
        self._obj = pandas_obj

    @classmethod
    def _validate(cls, obj):
        if not cls.required_columns.issubset(obj.columns):
            missing = cls.required_columns - set(obj.columns)
            raise AttributeError(f"DataFrame must have the following columns: {', '.join(cls.required_columns)}. "
                                 f"Missing columns: {', '.join(missing)}")


    def by(self, **kwargs):
        """
        get data from by value of column
        """
        obj = self._obj.copy()
        for by, value in kwargs.items():
            obj = self._single_get_by(obj, by, value)

        return obj

    def _single_get_by(self, obj, by, value):
        if by not in self._obj.columns:
            raise ValueError(f"Column '{by}' not found in DataFrame")
        return obj.loc[obj[by] == value].copy()


@register_dataframe_accessor("peak")
class PeakAccessor(BaseTableAccessor):
    required_columns = {'start', 'end', 'type', 'lv', 'st_px', 'en_px', 'stock_id'}

    def summary(self):
        # Method to return a summary of the peak data
        return {
            'total_peaks': self._obj.shape[0],
            'unique_stocks': self._obj['stock_id'].nunique(),
            'highest_lv': self._obj['lv'].max(),
            # Add more summary statistics as needed
        }

    def get_latest_peak(self, **kwargs):
        """
        kwargs: column->value filter
        """
        # Method to return the latest peak
        obj = self.by(**kwargs)
        return obj.loc[max(obj['end'])]