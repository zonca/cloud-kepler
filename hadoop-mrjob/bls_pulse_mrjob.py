#!/usr/bin/env python
from mrjob.job import MRJob
import mrjob.protocol
import re

FOLDER = "/oasis/scratch/zonca/temp_project/MAST/cloud-kepler/python/"

class BLSPulse(MRJob):
    """For testing purposes I am using the python scripts as bash scripts,
using mrjob only for setting up Hadoop"""

    INPUT_PROTOCOL = mrjob.protocol.RawValueProtocol
    INTERNAL_PROTOCOL = mrjob.protocol.RawValueProtocol
    OUTPUT_PROTOCOL = mrjob.protocol.RawValueProtocol

    def steps(self):
        return [
            self.mr(mapper_cmd=FOLDER + "download.py",
                    reducer_cmd=FOLDER + "join_quarters.py"),
            self.mr(reducer_cmd=FOLDER + "bls_pulse_vec_interface.py --mindur .01 --maxdur 2.0 --nbins 100 --segment 2.5 --direction -1 --printformat 'normal'")
        ]

if __name__ == '__main__':
    BLSPulse.run()
