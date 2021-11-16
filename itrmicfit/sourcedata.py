from pandas import DataFrame
from numpy import nan, newaxis, array, arange
from math import isnan
from typing import List


class SourceData:
    """Container for original data and their normalization"""
    data: DataFrame
    dilution_factor: float = 2.0
    initial_concentrations: List[float]
    names: List[str]
    concentrations: DataFrame = None
    values_normalized: DataFrame = None
    valid_cols: List[str]

    def __init__(self, data):
        self.data = data
        self.initial_concentrations = [1]*len(self.data)
        self.gather_names()
        self.gather_concentrations()
        self.valid_cols = ['0', '1', '2', '3', '4', '5', '6', '7', '8']

    @property
    def length(self):
        return len(self.data)

    def gather_names(self):
        if len(self.data['name'].values) > 0:
            self.names = self.data['name'].replace(nan, '').values
            self.reset_names()

    def gather_concentrations(self):
        if len(self.data['initial_concentration'].values) > 0:
            concentrations = []
            for i in self.data['initial_concentration'].values:
                if isnan(i):
                    concentrations.append(1.0)
                else:
                    try:
                        concentrations.append(float(i))
                    except ValueError:
                        concentrations.append(1.0)
            self.initial_concentrations = concentrations

    def reset_names(self):
        if self.concentrations is not None:
            self.concentrations['name'] = self.names
        if self.values_normalized is not None:
            self.values_normalized['name'] = self.names
        self.data['name'] = self.names

    def calculate(self):
        source_df = self.data

        # Blanks are used from the whole plate
        blank = (source_df['blank'] + source_df['blank2']) / 2

        data = source_df[self.valid_cols]

        self.values_normalized = (data.sub(blank, axis='rows')).div(
            source_df['bacterial_control'].sub(blank, axis='rows'), axis='rows')

        dilution_factors = self.dilution_factor ** (arange(0, 9, 1))
        self.concentrations = DataFrame(array(self.initial_concentrations)[:, newaxis] / dilution_factors)
        self.reset_names()
        self.concentrations.index = self.values_normalized.index
        self.data.index = self.values_normalized.index
