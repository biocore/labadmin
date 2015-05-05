__author__ = "Adam Robbins-Pianka"
__copyright__ = "Copyright 2009-2015, QIIME Web Analysis"
__credits__ = ["Adam Robbins-Pianka"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = ["Adam Robbins-Pianka"]
__email__ = "adam.robbinspianka@colorado.edu"
__status__ = "Development"


def combine_barcodes(cli_barcodes=None, input_file=None):
    """Combines barcodes specified from file and CLI into one set

    Note that both parameters are optional, and if this function is called
    without parameters, an empty set will be returned

    Parameters
    ----------
    cli_barcodes : tuple of string-like, optional
        Barcodes specified on the command line
    input_file : file or file-like object, optional
        One barcode per line. Must support iteration "for line in input_file"

    Returns
    -------
    set
        A set of all the barcodes, representing the union of the barcodes
        specified in the input file and the barcodes specified on the CLI
    """
    # Get barcodes from CLI if they were provided
    if cli_barcodes is not None:
        # barcodes come from click as unicode; convert to str
        cli_barcodes = {str(barcode) for barcode in cli_barcodes}
    else:
        cli_barcodes = set()

    # Get barcodes from file if it was provided
    if input_file is not None:
        file_barcodes = {line.strip() for line in input_file}
    else:
        file_barcodes = set()

    # return the union of those two sets
    return cli_barcodes | file_barcodes
