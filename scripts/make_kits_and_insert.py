#!/usr/bin/env python

__author__ = "Emily TerAvest"
__copyright__ = "Copyright 2009-2013, QIIME Web Analysis"
__credits__ = ["Emily TerAvest", "Daniel McDonald"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = ["Emily TerAvest"]
__email__ = "emily.teravest@colorado.edu"
__status__ = "Development"

import click
from random import choice

from passlib.hash import bcrypt

from amgut.connections import ag_data



# character sets for kit id, passwords and verification codes
KIT_ALPHA = "abcdefghjkmnpqrstuvwxyz"  # removed l and o for clarity
KIT_PASSWD = '1234567890'
KIT_VERCODE = KIT_PASSWD
KIT_PASSWD_NOZEROS = KIT_PASSWD[0:-1]
KIT_VERCODE_NOZEROS = KIT_PASSWD_NOZEROS


def determine_swabs(donationfile):
    """Determines number of kits with each number of swabs in the input file
    """
    lines = [l.strip().split('\t') for l in open(donationfile, 'U')]
    headers = [col.lower() for col in lines[0]]

    perks_to_swabs = {
        "Find Out Who\xd5s In Your Gut": {'swabs': 1, 'cost': 99.0},
        "You Plus The World": {'swabs': 1, 'cost': 129.0},
        "Microbes For Two: See What You\xd5re Sharing": {'swabs': 2,
                                                         'cost': 180.0},
        "Microbes For Three": {'swabs': 3, 'cost': 260.0},
        "Microbes For Four": {'swabs': 4, 'cost': 320.0},
        "A Week Of Feces": {'swabs': 7, 'cost': 500.0}
    }

    # this is updated with counts while the file is read and returned at end
    num_swab_to_kits = {1: 0, 2: 0, 3: 0, 4: 0, 7: 0}

    no_perk_claimed = []
    bad_amount = []
    bad_qty = []
    not_US = []

    for l in lines[1:]:
        line_dict = dict(zip(headers, l))

        amount = line_dict['amount'].replace(",", "")

        try:
            amount = float(amount)
        except ValueError:
            bad_amount.append("\t".join(l))
            continue

        if line_dict['perks claimed'] == '-':
            no_perk_claimed.append('\t'.join(l))
            continue

        # perks should be of the form, e.g., "1 x Who's In Your Gut"
        # so splitting on ' x ' should result in a 2-element list
        qty_perk = line_dict['perks claimed'].split(' x ')
        if not len(qty_perk) == 2:
            bad_qty.append('\t'.join(l))
            continue

        try:
            qty = int(qty_perk[0])
        except ValueError:
            bad_qty.append('\t'.join(l))
            continue

        perk_claimed = qty_perk[1]
        try:
            num_swabs = perks_to_swabs[perk_claimed]['swabs']
            amt_needed = qty * perks_to_swabs[perk_claimed]['cost']
        except KeyError:
            no_perk_claimed.append('\t'.join(l))
        if line_dict['amount'] < amt_needed:
            bad_amount.append('\t'.join(l))
            continue

        if line_dict['country'] != 'US':
            not_US.append('\t'.join(l))
            continue

        #return a dictionary with the number of kits with each number of swabs
        if num_swabs in num_swab_to_kits:
            num_swab_to_kits[num_swabs] += qty
        else:
            num_swab_to_kits[num_swabs] = qty

    if bad_amount:
        print "Kits with bad amounts:\n"
        print '\n'.join(bad_amount)
    if no_perk_claimed:
        print "\n\nNo perk claimed:\n"
        print '\n'.join(no_perk_claimed)
    if not_US:
        print "\n\nInterantaional Participants:\n"
        print '\n'.join(not_US)
    if bad_qty:
        print "\n\nBad Quantity (for number of perks claimed):\n"
        print '\n'.join(bad_qty)

    return num_swab_to_kits


def verify_unique_sample_id(cursor, sample_id):
    """Verify that a sample ID does not already exist
    """
    sql = "select barcode from barcode where barcode = %s"
    cursor.execute(sql, [sample_id])
    results = cursor.fetchall()
    return len(results) == 0


def get_used_kit_ids(cursor):
    """Grab in use kit IDs, return set of them
    """
    cursor.execute("select supplied_kit_id from ag_kit")

    return set([i[0] for i in cursor.fetchall()])


def make_kit_id(kit_id_length=5, tag=None):
    if kit_id_length > 9:
        #database table has 9 chars for the kit_id_length
        kit_id_length = 9

    if tag is None:
        kit_id = ''.join([choice(KIT_ALPHA) for i in range(kit_id_length)])
    else:
        if (kit_id_length + len(tag) + 1) > 9:
            #we have a 9 char limit for kit ids reduce the kit_id_length
            kit_id_length = 8 - len(tag)
        kit_id = ''.join([choice(KIT_ALPHA) for i in range(kit_id_length)])
        kit_id = tag + '_' + kit_id

    return kit_id


def make_valid_kit_id(obs_kit_ids, kit_id_length=5, tag=None):
    """Generate a new unique kit id

    obs_kit_ids : kit identifiers that have already been used in the database

    """

    kit_id = make_kit_id(kit_id_length, tag)
    while kit_id in obs_kit_ids:
        kit_id = make_kit_id(kit_id_length, tag)

    obs_kit_ids.add(kit_id)

    return (obs_kit_ids, kit_id)


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


def get_printout_data(kit_passwd_map, kit_barcode_map):
    """Produce the text for paper slips with kit credentials
    """
    BASE_PRINTOUT_TEXT = """Thank you for participating in the American Gut \
Project! Below you will find your sample barcodes (the numbers that \
anonymously link your samples to you) and your login credentials. It is very \
important that you login before you begin any sample collection.

Please login at: http://www.microbio.me/AmericanGut

Thanks,
The American Gut Project
"""
    text = []
    for kit_id, passwd in kit_passwd_map:
        text.append(BASE_PRINTOUT_TEXT)
        barcodes = kit_barcode_map[kit_id]

        padding_lines = 5

        if len(barcodes) > 5:
            text.append("Sample Barcodes:\t%s" % ', '.join(barcodes[:5]))
            for i in range(len(barcodes))[5::5]:
                padding_lines -= 1
                text.append("\t\t\t%s" % ', '.join(barcodes[i:i+5]))
        else:
            text.append("Sample Barcodes:\t%s" % ', '.join(barcodes))

        text.append("Kit ID:\t\t%s" % kit_id)
        text.append("Password:\t\t%s" % passwd)

        # padding between sheets so they print pretty
        for i in range(padding_lines):
            text.append('')

    return text


def unassigned_kits(starting_sample, cursor, existing_kit_ids, output,
                    swabs_per_kit, tag=None):
    """Creates handout kits based on number of kits need for each swab count
    """
    header = ["barcode", "swabs_per_kit", "KIT_ID", "KIT_PASSWORD",
              "KIT_VERIFICATION_CODE", "SAMPLE_BARCODE_FILE"]

    outlines = [header[:]]

    kit_barcode_map = {}
    kit_passwd_map = []
    current_sample_id = starting_sample

    for swab_count in swabs_per_kit:
        kit_count = swabs_per_kit[swab_count]
        for kit in range(kit_count):
            existing_kit_ids, kit_id = make_valid_kit_id(existing_kit_ids,
                                                         tag=tag)
            passwd = make_passwd()
            vercode = make_verification_code()

            kit_barcode_map[kit_id] = []
            kit_passwd_map.append((kit_id, passwd))

            # add on the samples per kit
            for sample in range(swab_count):
                sample_id = "%0.9d" % current_sample_id

                if not verify_unique_sample_id(cursor, sample_id):
                    raise ValueError("%s is not unique!" % sample_id)

                outlines.append([sample_id, swab_count, kit_id, passwd,
                                 vercode, "%s.jpg" % sample_id])
                kit_barcode_map[kit_id].append(sample_id)

                current_sample_id += 1

    f = open(output, 'w')
    f.write('\n'.join(['\t'.join(map(str, l)) for l in outlines]))
    f.write('\n')
    f.close()

    return kit_passwd_map, kit_barcode_map, outlines


def make_printouts(kit_passwd_map, kit_barcode_map, output):
    """Makes a file with the kit creditinal infomration
    """
    f = open(output + '.printouts', 'w')
    f.write('\n'.join(get_printout_data(kit_passwd_map, kit_barcode_map)))
    f.write('\n')
    f.close()


def insert_kits(kits, proj_id, cursor):
    """inserts the handout kits into the test database and the
       prodction database.
    """
    #skip the header line
    for line in kits[1:]:
        #line continuations are on lines below to prevent newlines being in the
        #output files.
        #first insert handout kits
        barcode, spk, kid, password, vercode, sbf = line[:6]
        password = bcrypt.encrypt(password)

        kitinsertstmt = ("insert into ag_handout_kits (barcode, "
                         "swabs_per_kit,KIT_ID,PASSWORD,VERIFICATION_CODE, "
                         "SAMPLE_BARCODE_FILE) values "
                         "('%s','%s', '%s', '%s', '%s', '%s')" %
                        (barcode, spk, kid, password, vercode, sbf))

        barcodeinsertstmt = ("insert into barcode (barcode, obsolete) "
                             "values ('%s', 'N')" % barcode)

        #this statment will need updated when group info is on live
        barcodeprojinsertstmt = ("insert into project_barcode (barcode, "
                                 "project_id) values ('%s', '%s')" %
                                 (barcode, proj_id))
        #print kitinsertstmt
        #print barcodeinsertstmt
        #print barcodeprojinsertstmt
        cursor.execute(kitinsertstmt)
        cursor.execute(barcodeinsertstmt)
        cursor.execute(barcodeprojinsertstmt)
        cursor.execute('commit')


@click.command()
@click.option('--dry_run/--real', default=False,
              help='This flag prevents writes to the database')
@click.option('--output', required=True, help="Output filename")
@click.option('--project_name', required=True, help=('Prjoect Name for the'
              'barcodes \nAs of (4/04/14) Possible projects are: \n'
              '"American Gut Project" \n'
              '"ICU Microbiome" \n'
              '"Handout Kits" \n'
              '"Office Succession Study" \n'
              '"American Gut Project: Functional Feces" \n'
              '"Down Syndrome Microbiome" \n'
              '"Beyond Bacteria" \n'
              '"All in the Family" \n'
              '"Sloan Toronto House" \n'
              '"American Gut Handout kit" \n'
              '"Personal Genome Project" \n'
              '"Sleep Study"'
              ''))
@click.option('--swabs_to_kits', required=False, help=('dict of swabs to kits '
              'example format:"{1:10,2:5}"'))
@click.option('--input', required=False, help='input file of participant info')
@click.option('--tag', required=False, help='prefix tag, tag_kitid will be '
              'format do not include underscore in tag')
def make_kits_and_insert(output, project_name, swabs_to_kits, input, tag,
                         dry_run):
    """"This progam creates hand out
        kits and inputs them into the database.
        Required inputs are the name of an output
        file, and the project name for the barcodes.
        Either a tab separated spreadsheet or a
        dictionary of swabs to number of kits is
        requried as input
    """
#    option_parser, opts, args = parse_command_line_parameters(**script_info)
    #args = parser.parse_args()

    # setup DB connection
    #cred = Credentials()
    #con = connect(cred.liveMetadataDatabaseConnectionString)
    #cursor = con.cursor()
    cursor = ag_data.connection.cursor()
    existing_kit_ids = get_used_kit_ids(cursor)

    #tag = args.tag
    proj_name = project_name
    sql = "select project_id from project where project = %s"
    cursor.execute(sql, [proj_name])
    proj_id = cursor.fetchone()
    if proj_id is None:
        print "Project Name must be exactly the same as in the database"
        print "Project Name '%s' is not in the database" % proj_name
        exit()
    else:
        proj_id = proj_id[0]
    if input is not None:
        swabs_to_kits = determine_swabs(input)
    elif swabs_to_kits is not None:
        swabs_to_kits_string = swabs_to_kits
        swabs_to_kits = {}
        #incomeing format is {#:#,#:#,#:#}
        for pair in swabs_to_kits_string.strip("{").strip("}").split(","):
            pair = pair.split(':')
            swabs_to_kits[int(pair[0])] = int(pair[1])
    else:
        print "Must specify either input file or swabs to kits dictionary"
        exit()
    starting_sample, text_barcode = ag_data.getNextAGBarcode()
    #output = args.output
    kit_passwd_map, kit_barcode_map, outlines = \
        unassigned_kits(starting_sample, cursor, existing_kit_ids, output,
                        swabs_to_kits, tag)
    make_printouts(kit_passwd_map, kit_barcode_map, output)
    #testcon = connect(cred.testMetadataDatabaseConnectionString)
    #testcursor = testcon.cursor()
    if not dry_run:
        #try:
        #    insert_kits(outlines, proj_id, testcursor)
        #    testcursor.close()
        #except:
        ##    #if anything happens raise and exit
        #    testcursor.close()
        #    print "error when uploading to test database"
        #    raise

        try:
            insert_kits(outlines, proj_id, cursor)
        except:
            print "error while uploading to production database"
            cursor.close()
            raise
    cursor.close()


if __name__ == '__main__':
    make_kits_and_insert()
