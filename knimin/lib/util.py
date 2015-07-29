__author__ = "Adam Robbins-Pianka"
__copyright__ = "Copyright 2009-2015, QIIME Web Analysis"
__credits__ = ["Adam Robbins-Pianka"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = ["Adam Robbins-Pianka"]
__email__ = "adam.robbinspianka@colorado.edu"
__status__ = "Development"

from random import choice

# character sets for kit id, passwords and verification codes
KIT_ALPHA = "abcdefghjkmnpqrstuvwxyz"  # removed l and o for clarity
KIT_PASSWD = '1234567890'
KIT_VERCODE = KIT_PASSWD
KIT_PASSWD_NOZEROS = KIT_PASSWD[0:-1]
KIT_VERCODE_NOZEROS = KIT_PASSWD_NOZEROS


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


def make_valid_kit_ids(num_ids, obs_kit_ids, kit_id_length=5, tag=None):
    """Generates new unique kit IDs

    Parameters
    ----------
    num_ids : int
        Number of kit IDs to create
    obs_kit_ids : set
        Already used kit IDs in the database
    kit_id_length : int, optional
        number of characters in kit_id created, default 5. Must be <= 9
    tag : str, optional
        tag to prepend to kit_id, defaut none

    Returns
    -------
    list
        New kit IDs created
    """
    if kit_id_length > 9:
            # database table has 9 chars for the kit_id_length
            kit_id_length = 9

    if tag is not None:
        if (kit_id_length + len(tag) + 1) > 9:
            # we have a 9 char limit so reduce the kit_id_length
            kit_id_length = 8 - len(tag)
        tag += '_'
    else:
        tag = ''

    def make_kit_id(kit_id_length, tag):
        kit_id = ''.join([choice(KIT_ALPHA) for i in range(kit_id_length)])
        kit_id = tag + kit_id
        return kit_id

    # Create the new kit IDs
    new_ids = []
    for i in range(num_ids):
        kit_id = make_kit_id(kit_id_length, tag)
        while kit_id in obs_kit_ids:
            kit_id = make_kit_id(kit_id_length, tag)
        new_ids.append(kit_id)
        obs_kit_ids.add(kit_id)

    return new_ids


def make_passwd(passwd_length=8):
    """Generate a new password
    """
    x = ''.join([choice(KIT_PASSWD) for i in range(passwd_length-1)])
    return choice(KIT_PASSWD_NOZEROS) + x


def make_verification_code(vercode_length=5):
    """Generate a verification code
    """
    x = ''.join([choice(KIT_VERCODE) for i in range(vercode_length-1)])
    return choice(KIT_VERCODE_NOZEROS) + x
