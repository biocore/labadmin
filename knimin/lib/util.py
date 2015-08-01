__author__ = "Adam Robbins-Pianka"
__copyright__ = "Copyright 2009-2015, QIIME Web Analysis"
__credits__ = ["Adam Robbins-Pianka"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = ["Adam Robbins-Pianka"]
__email__ = "adam.robbinspianka@colorado.edu"
__status__ = "Development"

from random import choice
from amgut.connections import ag_data

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


def get_printout_data(kitinfo):
    """Produce the text for paper slips with kit credentials & mapping table
    """
    BASE_PRINTOUT_TEXT = """Thank you for participating in the American Gut \
Project! Below you will find your sample barcodes (the numbers that \
anonymously link your samples to you) and your login credentials. It is very \
important that you login before you begin any sample collection.

Please login at: http://www.microbio.me/AmericanGut

Thanks,
The American Gut Project
"""
    kit_id = 0
    password = 1
    ver_code = 2
    bcs = 3

    text = []
    for kit in kitinfo:
        text.append(BASE_PRINTOUT_TEXT)
        barcodes = kit[bcs]

        padding_lines = 5

        if len(barcodes) > 5:
            text.append("Sample Barcodes:\t%s" % ', '.join(barcodes[:5]))
            for i in range(len(barcodes))[5::5]:
                padding_lines -= 1
                text.append("\t\t\t%s" % ', '.join(barcodes[i:i+5]))
        else:
            text.append("Sample Barcodes:\t%s" % ', '.join(barcodes))

        text.append("Kit ID:\t\t%s" % kit[kit_id])
        text.append("Password:\t\t%s" % kit[password])

        # padding between sheets so they print pretty
        for i in range(padding_lines):
            text.append('')

    return '\n'.join(text)


def make_valid_kit_ids(num_ids, obs_kit_ids, kit_id_length=5, tag=None):
    """Generates new unique kit IDs

    Parameters
    ----------
    num_ids : int
        Number of kit IDs to create
    obs_kit_ids : set
        Already used kit IDs in the database
    kit_id_length : int, optional
        number of characters in base kit_id created, default 5. Must be <= 9
    tag : str, optional
        tag to prepend to kit_id, defaut none. Maximum 4 characters

    Returns
    -------
    list
        New kit IDs created

    Raises
    ------
    ValueError
        Tag is more than 4 characters long
        More kits requested than possible kit ID combinations

    Notes
    -----
    If id length is > 9, it will be set to 9. This length includes the
    passed kit_id_length + tag length + 1 for an underscore seperator.
    Because of this, kit_id_length should be kept short.
    """

    if tag is not None:
        if len(tag) > 4:
            raise ValueError("Tag must be 4 or less characters")
        if (kit_id_length + len(tag) + 1) > 9:
            # we have a 9 char limit so reduce the kit_id_length
            kit_id_length = 8 - len(tag)
        tag += '_'
    else:
        tag = ''

    if kit_id_length > len(KIT_ALPHA)**kit_id_length:
        raise ValueError("More kits requested than possible kit ID combos!")

    obs_kit_ids = ag_data.get_used_kit_ids()

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
