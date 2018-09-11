#now fitting the sine function
import numpy as np
from scipy.optimize import leastsq

def sineFit2Cycle(data,nT):
    N=len(data)
    t = np.linspace(0, nT*2*np.pi, N)
    guess_mean = np.mean(data)
    guess_std = 3*np.std(data)/(2**0.5)
    guess_phase = 0

    # Define the function to optimize, in this case, we want to minimize the difference
    # between the actual data and our "guessed" parameters
    optimize_func = lambda x: x[0]*np.sin(t+x[1]) + x[2] - data
    est_std, est_phase, est_mean = leastsq(optimize_func, [guess_std, guess_phase, guess_mean])[0]
    return est_std, est_phase, est_mean