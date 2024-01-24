import pandas as pd
from lmfit import Model
import numpy as np
import matplotlib.pyplot as plt


# Define the bi-exponential function
def bi_exponential(x, a, b, c, d, e):
    """
        Define the bi-exponential function.

        :param x: Independent variable
        :param a: Amplitude of the first exponential
        :param b: Decay rate of the first exponential
        :param c: Amplitude of the second exponential
        :param d: Decay rate of the second exponential
        :param e: Steady state current
        :return: Evaluated bi-exponential function at x
        """
    return a * np.exp(-x * b) + c * np.exp(-x * d) + e


# Fit the bi-exponential function to the data using lmfit
def fit_bi_exponential_lmfit(xdata, ydata):
    """
    Fit the bi-exponential function to the provided data using lmfit.

    :param xdata: Array-like, the independent variable
    :param ydata: Array-like, the dependent variable
    :return: lmfit model result containing the fitted parameters and other statistical details
    """
    try:
        # Create a Model based on the bi_exponential function
        model = Model(bi_exponential)

        # Create parameters with initial values and optionally bounds
        params = model.make_params(a=0.2, b=0.01, c=0.3, d=0.1, e=-20)
        # Example of setting bounds: params['a'].set(min=0, max=10)

        # Fit the model to the data
        results = model.fit(ydata, params, x=xdata)

        return results
    except Exception as e:
        print(f"An error occurred during curve fitting with lmfit: {e}")
        return None


data_file = "D:/Seafile/Code/DataExamples/TrAMPPT_example.txt"
data_df = pd.read_csv(data_file, sep="\t", header=None, decimal=",")


x1 = data_df.iloc[:, 0].values
y1 = data_df.iloc[:, 1].values
# x1 = data_df.iloc[:, 2].values
# y1 = data_df.iloc[:, 3].values

x1 = x1-min(x1)


result = fit_bi_exponential_lmfit(x1, y1)

# Plot the results
plt.scatter(x1, y1, label='Data')
smooth_x = np.linspace(min(x1), max(x1), 500)
smooth_y = bi_exponential(smooth_x, *result.params.valuesdict().values())

plt.plot(smooth_x, smooth_y, label='Fitted curve', color='red', linewidth=2)

print(result.fit_report())

plt.legend()
plt.show()
