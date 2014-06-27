#include <math.h>
#include <stdio.h>

#define min(a,b)        (a < b ? a : b)
#define max(a,b)        (a > b ? a : b)


int do_bls_pulse_segment(double *time, double *flux, double *fluxerr, double *samples,
    int nbins, int n, int nbins_min_dur, int nbins_max_dur, double *srsq, 
    double *duration, double *depth, double *midtime)
{
    /**
     * This function takes an array of time, flux, error, and weights (number of samples 
     * per bin), all of size `nbins`, and writes to the arrays `srsq`, `duration`,
     * `depth`, and `midtime`, assumed to be pre-allocated and of the same size. There
     * is no handling of NaN values; they should be filtered out before calling; this
     * means that `nbins` is actually the number of non-NaN bins.
     */
   
    int i, j, k, bestdur;
    double s, r, d, srsqmax, srsqnew, bestdepth;
    double nn = (double) n;

    for (i = 0; i < nbins - nbins_min_dur; i++)
    {
        /* minimum possible value is 0 */
        srsqmax = 0.;
        
        s = 0.;
        r = 0.;
        d = flux[i];

        /* Instead of looping from i to j inside the j loop, we can precompute this
         * part of the sum, which is independent of j. So we avoid having three 
         * nested loops. */
        for (k = i; k < i + nbins_min_dur; k++)
        {
            s += flux[k];
            r += samples[k];
            d = min(d, flux[k]);
        }
        
        for (j = min(i + nbins_min_dur, nbins); j < min(i + nbins_max_dur, nbins); j++)
        {
            /* i and j will always be valid values for i1, i2 as defined in the algorithm
             * of Kovacs, Zucker, & Mazeh (2002). */

            s += flux[j];
            r += samples[j];
            d = fmin(d, flux[j]);
            
            srsqnew = (s * s) / (r * (nn - r));
            
            if (srsqnew > srsqmax)
            {
                /* We found a better event than previously; overwrite the "best" 
                 * parameters. */
                srsqmax = srsqnew;
                bestdur = j;        /* this is an index, not a time! */
                bestdepth = d;      /* this is an absolute level, not relative */
            }
        }           

        /* Save the best parameters for events starting at each bin. */
        srsq[i] = srsqmax;
        duration[i] = time[bestdur] - time[i];
        depth[i] = bestdepth;
        midtime[i] = (time[bestdur] + time[i]) / 2.;
    }

    return 0;
}

