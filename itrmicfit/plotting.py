import numpy as np
from typing import List
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from .fitting import Fit, FitType, MICQuality, interpolate_curve_df_and_fitted


def plot_to_file(self, file, elements):
    fig = plt.figure(1, (10, 5), tight_layout=True)
    plot(elements, fig=fig)
    fig.savefig(file, dpi=600)


def plot(data: List[Fit], fig: Figure):
    curve_interpolated = None
    hmax = None
    mic_title = ""

    nb = np.min([2, len(data)])
    no = (len(data) + 1) // 2
    ax = fig.subplots(nb, no)

    # Need to decouple curve making and values calculation
    for index, fit in enumerate(data):
        if len(data) == 1:
            axis = ax
        else:
            axis = ax.flatten()[index]

        fit.original_curve.plot(x='x', y=['measured'], kind='scatter', c='red', ax=axis)
        curve_fitted = fit.fitted_curve
        if curve_fitted is not None:
            curve_interpolated = interpolate_curve_df_and_fitted(fit.original_curve, curve_fitted)
            curve_interpolated.plot(x='x', y=['fitted'], ax=axis)
        background = "#FFFFFF"
        mic_line_color = None
        if fit.type_of_fit == FitType.NOT_FITTED:
            background = "#FFB0B0"
            if fit.mic.concentration is not None:
                mic_title += f"{fit.mic.concentration:.2}"
                mic_title += " Cannot be fitted"
        elif fit.type_of_fit == FitType.FITTED:
            mic_title = f"MIC{fit.mic.percentage * 100}"

            if isinstance(fit.mic.concentration, str):
                mic_title += f"{fit.mic.concentration}"
            elif fit.mic.concentration is not None:
                mic_title += f"={fit.mic.concentration:.2}"

            if fit.mic.quality == MICQuality.OVER_MEASURED_RANGE:
                mic_line_color = "#A08000"
                background = "#FFAFAF"
                if not isinstance(fit.mic.concentration, str) and fit.mic.concentration is not None:
                    if curve_interpolated is not None:
                        hmax = np.max((fit.mic.concentration, curve_interpolated.x.max()))
                    else:
                        hmax = fit.mic.concentration
                        print(hmax)
                else:
                    hmax = fit.original_curve.x.max()
            elif fit.mic.quality == MICQuality.OK:
                background = "#AFFFAF"
                mic_line_color = "#004F00"
                hmax = np.max((fit.mic.concentration, curve_interpolated.x.max()))
            elif fit.mic.quality == MICQuality.POOR:
                background = "#DFFFAF"
                mic_line_color = "#00FF00"
                if isinstance(fit.mic.concentration, np.float64):
                    hmax = np.max((fit.mic.concentration, curve_interpolated.x.max()))
                elif fit.mic.concentration.isnumeric():
                    print(fit.mic.concentration)
                    print(curve_interpolated.x.max())
                    hmax = np.max((fit.mic.concentration, curve_interpolated.x.max()))
                else:
                    hmax = curve_interpolated.x.max()
            elif fit.mic.quality == MICQuality.ESTIMATED_FROM_INTERPOLATION:
                background = "#FFE0A0"
                mic_title += " - Estimated from interpolation"
                mic_line_color = "#A0FF00"
                hmax = fit.mic.concentration * 2
            else:
                background = "#FFA0A0"
                mic_title += " - Cannot find an MIC"
                mic_line_color = None

        if mic_line_color is not None:
            if isinstance(fit.mic.concentration, np.float64):
                axis.vlines(fit.mic.concentration, 0, 1, color=mic_line_color)
            if hmax is not None:
                axis.hlines(1 - fit.mic.percentage, 0, hmax, color="#004F00")

        axis.set_title(f"{fit.name} {mic_title}")
        axis.set_facecolor(background)
        axis.set_xlabel('')
        axis.set_ylabel("Growth")
