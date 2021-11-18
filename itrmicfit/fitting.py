from scipy import interpolate
import numpy as np
from pandas import DataFrame
from scipy.optimize import curve_fit, fsolve
from typing import List, Any
from dataclasses import dataclass
from enum import Enum
from uncertainties import ufloat

from .sourcedata import SourceData


def hill_4p_function(concentration, d0i: float = 0.01, n: float = 10, s: float = 1, o: float = 0):
    """Hill 4p same as Hill 3p but with offset"""
    return o + s / (1 + (concentration / d0i) ** n)


def curve_to_dataframe(curve):
    """Returns a Dataframe with that curve data in"""
    return DataFrame(curve, columns=["x", "measured"])


def fit_hill_4p(curve_df):
    """Take the curve generated earlier and get the (popt, pcov, and function) of a fit of the hill 4p function"""
    return (*curve_fit(hill_4p_function, curve_df.x.values, curve_df.measured.values,
                       bounds=((curve_df.x.min(), 0.01, 0.1, 0.01), (curve_df.x.max(), 6, 4, 1))), hill_4p_function)


def interpolate_curve_df_and_fitted(curve_df, curve_fitted, points=1000):
    x = np.linspace(curve_df.x.values.min(), curve_df.x.values.max(), num=points, endpoint=True)
    f = interpolate.interp1d(curve_df.x, curve_df.measured)
    df = DataFrame({'x': x, 'measured': f(x), 'fitted': curve_fitted[2](x, *curve_fitted[0])})
    return df


def interpolate_cspline(curve_df):
    sorted_df = curve_df.sort_values(by=['x'])

    tck = interpolate.splrep(sorted_df.x, sorted_df.measured, s=0)

    def fun(x):
        return interpolate.splev(x, tck, der=0)

    return fun


def mic_intersect_prep(curve_fitted, limit=0.1):
    def mic_intersect(x):
        return curve_fitted[2](x, *curve_fitted[0]) - (1 - limit)

    return mic_intersect


def mic_intersect_interpolated_prep(f, limit=0.1):
    def mic_intersect(x):
        return f(x) - (1 - limit)

    return mic_intersect


class FitType(Enum):
    NOT_FITTED = "Not fitted"
    FITTED = "Fitted"


class MICQuality(Enum):
    NOT_DETERMINED = "Not determined"
    OK = "Ok"
    POOR = "Poor"
    OVER_MEASURED_RANGE = "Over measured range"
    UNDER_MEASURED_RANGE = "Under measured range"
    ESTIMATED_FROM_INTERPOLATION = "Estimated from interpolation"
    OVER_MEASURED_RANGE_NOT_FITTED = "Over measured range, not fitted"


@dataclass
class MIC:
    """An MIC value"""
    concentration: float
    percentage: float
    quality: MICQuality


@dataclass
class Fit:
    """Information about a specific fitting"""
    name: str
    type_of_fit: FitType
    mic: MIC
    original_curve: DataFrame
    fitted_curve: Any = None
    uncertainties: Any = None


def group_by_name_and_widen(df):
    s = df.groupby("name").cumcount()

    df1 = df.set_index(['name', s]).unstack().sort_index(level=1, axis=1)
    df1.columns = [f'{x}-{y}' for x, y in df1.columns]
    df1 = df1.reset_index()
    return df1.dropna(axis=1)


def fit_from_sourcedata(data: SourceData, n: float) -> List[Fit]:
    """Fit the curves from `data`, and estimate MICn
       where n is [0,1]
    """
    fits = []

    # Need to decouple curve making and values calculation
    all_concentrations = group_by_name_and_widen(data.concentrations)
    all_values = group_by_name_and_widen(data.values_normalized)
    for substance in set(data.concentrations.name):
        percentage = n
        concentration = None
        quality = MICQuality.NOT_DETERMINED


        # Using the approch from:
        # https://stackoverflow.com/questions/56071160/combine-multiple-rows-in-pandas-dataframe-and-create-new-columns

        concentrations = all_concentrations[all_concentrations.name == substance].drop("name", axis=1).iloc[0, :]
        measured = all_values[all_values.name == substance].drop("name", axis=1).iloc[0, :]

        name = substance
        curve_df = DataFrame({'x': concentrations.values, 'measured': measured.values})
        _d0i = None
        _n = None
        _s = None
        _o = None
        mic_error = None
        try:
            curve_fitted = fit_hill_4p(curve_df)
            sigmas = np.sqrt(np.diag(curve_fitted[1]))

            _d0i = ufloat(curve_fitted[0][0], sigmas[0])
            _n = ufloat(curve_fitted[0][1], sigmas[1])
            _s = ufloat(curve_fitted[0][2], sigmas[2])
            _o = ufloat(curve_fitted[0][3], sigmas[3])

            curve_interpolated = interpolate_curve_df_and_fitted(curve_df, curve_fitted)
            initial_value = curve_interpolated.x[(np.abs(curve_interpolated.fitted - (1 - n))).argmin()]
            solve = fsolve(mic_intersect_prep(curve_fitted, n), initial_value, factor=0.1, full_output=True, xtol=0.01)
            mic = solve[0][0]
            try:
                mic_error = _d0i * (_s / ((1 - n) - _o) - 1) ** (1 / _n)
            except ValueError:
                mic_error = None

            if solve[2] == 1 and curve_interpolated.fitted.min() < mic:
                # If the MIC is above the measured X value
                if mic > curve_interpolated.x.max():
                    quality = MICQuality.OVER_MEASURED_RANGE
                else:
                    quality = MICQuality.OK

                concentration = mic
            else:
                if mic > curve_df.x.max():
                    quality = MICQuality.OVER_MEASURED_RANGE

            if quality == MICQuality.OK:
                # We do not have a correct fit, we revert to a simple cubic splines interpolation
                cscurve = interpolate_cspline(curve_df)
                solve = fsolve(mic_intersect_interpolated_prep(cscurve, n), initial_value, factor=0.1, full_output=True,
                               xtol=0.01)
                csvalue = solve[0][0]

                if np.abs(curve_df.measured.min() - (1 - n)) < 0.01:
                    quality = MICQuality.ESTIMATED_FROM_INTERPOLATION
                    concentration = csvalue
            # If the searched is above the minimaly measured X value
            if (1-n) <= curve_df.measured.min():
                quality = MICQuality.OVER_MEASURED_RANGE
            elif (1-n) >= curve_df.measured.max():
                quality = MICQuality.UNDER_MEASURED_RANGE

            fit_type = FitType.FITTED
        except RuntimeError:
            fit_type = FitType.NOT_FITTED

            curve_fitted = None

        if quality == MICQuality.OVER_MEASURED_RANGE:
            concentration = f"> {max(curve_df.x)} ({100 * max(curve_df.measured) - 100:00.0f}%)"
        elif quality == MICQuality.UNDER_MEASURED_RANGE:
            concentration = f"< {min(curve_df.x)} ({100 - 100 * min(curve_df.measured):00.0f}%)"
        # if mic_error is not None:
        #    if mic_error.std_dev>mic_error.n*4:
        #        quality = MICQuality.POOR
        fits.append(Fit(name, fit_type, MIC(concentration, percentage, quality), curve_df, curve_fitted,
                        uncertainties={'d0i': _d0i, 'n': _n, 's': _s, 'o': _o, 'mic': mic_error}))

    return fits
