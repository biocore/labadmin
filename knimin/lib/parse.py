# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

import numpy as np


def parse_plate_reader_output(contents):
    """Parses the output of a plate reader

    The format supported here is a tab delimited file in which the first line
    contains the fitting curve followed by (n) blank lines and then a tab
    delimited matrix with the values

    Parameters
    ----------
    contents : str
        The contents of the plate reader output

    Returns
    -------
    np.array of floats
        A 2D array of floats
    """
    data = []
    for line in contents.splitlines():
        line = line.strip()
        if not line or line.startswith('Curve'):
            continue
        data.append(line.split())

    return np.asarray(data, dtype=np.float)
