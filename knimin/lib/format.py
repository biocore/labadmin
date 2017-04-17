import datetime


def format_epmotion_file(volumes, destination):
    """Writes an EPMotion file

    Parameters
    ----------
    volumes : 2d-numpy array of floats
        The volumes to transfer
    dest : int
        The destination tube
    """
    # Add the headers
    contents = ['Rack,Source,Rack,Destination,Volume,Tool']
    rows, cols = volumes.shape
    destination = str(destination)
    for i in range(rows):
        for j in range(cols):
            # 0 values get removed - this is good enough, no need to get fancy
            if volumes[i][j] < 0.001:
                continue
            # Hardcoded values: those never change
            source = "%s%d" % (chr(ord('a') + i), j+1)
            val = "%.3f" % volumes[i][j]
            contents.append(
                ",".join(['1', source, '1', destination, val, '1']))
    return "\n".join(contents)


def write_sample_sheet(output_fp, instrument_type, labadmin_id,
                       run_name, assay, fwd_cycles, rev_cycles,
                       pi_name, pi_email,
                       contact_0_name, contact_0_email,
                       run_type, sample_information,
                       contact_1_name=None, contact_1_email=None,
                       contact_2_name=None, contact_2_email=None):
    full_sheet = format_sample_sheet(output_fp, instrument_type,
                                     run_name, assay, fwd_cycles, rev_cycles,
                                     pi_name, pi_email,
                                     contact_0_name, contact_0_email,
                                     run_type, sample_information,
                                     contact_1_name, contact_1_email,
                                     contact_2_name, contact_2_email)
    with open(output_fp, 'w') as f:
        f.write(full_sheet)


def format_sample_sheet(instrument_type, labadmin_id,  # noqa: C901
                        run_name, assay, fwd_cycles, rev_cycles,
                        pi_name, pi_email,
                        contact_0_name, contact_0_email,
                        run_type, sample_information,
                        contact_1_name=None, contact_1_email=None,
                        contact_2_name=None, contact_2_email=None):
    """Writes a sample sheet

    Parameters
    ----------
    instrument_type : {miseq, hiseq}
        The instrument type.
    labadmin_id : int
        The ID of the sequencing run as informed by labadmin
    run_name : str
        The name of the run.
    assay : str
        The assay instrument (e.g., Kapa Hyper Plus)
    fwd_cycles : int
        The number of forward cycles
    rev_cycles : int
        The number of reverse cycles
    pi_name : str
        The name of the principle investigator
    pi_email : str
        The email address of the principle investigator
    contact_0_name : str
        The name of an additional contact person
    contact_0_email : str
        The email of an additional contact person
    run_type : {"Target Gene", "Shotgun"}
        Which data sheet structure to use
    sample_information : iterable of dict
        The sample information to load into the sample sheet. See note below.
    contact_1_name : str, optional
        The name of an additional contact.
    contact_1_email : str, optional
        The email of an additional contact.
    contact_2_name : str, optional
        The name of an additional contact.
    contact_2_email : str, optional
        The email of an additional contact.

    Sample Sheet Note
    -----------------
    If the instrument type is a MiSeq, any lane information per-sample will be
    disregarded. If instrument type is a HiSeq, each sample must include a
    "lane" key.

    If the run type is Target Gene, then sample details are disregarded
    with the exception of determining the lanes.

    IF the run type is shotgun, then the following keys are required:
        - sample-id
        - i7-index-id
        - i7-index
        - i5-index-id
        - i5-index

    Raises
    ------
    ValueError
        If a contact name is specified and an email is omitted, and vice versa
    ValueError
        If an unknown run type is specified
    ValueError
        If the number of cycles are <= 0
    ValueError
        If an unknown instrument type is specified.

    Return
    ------
    str
        The formatted sheet.
    """
    def validate_contact(name, email):
        if name is not None and email is None:
            raise ValueError("email is missing for %s" % name)
        elif name is None and email is not None:
            raise ValueError("name is missing for %s" % email)

    c1name = contact_1_name if contact_1_name is not None else ''
    c1email = contact_1_email if contact_1_email is not None else ''
    c2name = contact_2_name if contact_2_name is not None else ''
    c2email = contact_2_email if contact_2_email is not None else ''

    validate_contact(pi_name, pi_email)
    validate_contact(contact_0_name, contact_0_email)
    validate_contact(contact_1_name, contact_1_email)
    validate_contact(contact_2_name, contact_2_email)

    if fwd_cycles <= 0 or not isinstance(fwd_cycles, int):
        raise ValueError("fwd_cycles must be > 0")
    if rev_cycles <= 0 or not isinstance(rev_cycles, int):
        raise ValueError("rev_cycles must be > 0")

    if run_type == 'Target Gene':
        sample_header = DATA_TARGET_GENE_STRUCTURE
        sample_detail = DATA_TARGET_GENE_SAMPLE_STRUCTURE
    elif run_type == 'Shotgun':
        sample_header = DATA_SHOTGUN_STRUCTURE
        sample_detail = DATA_SHOTGUN_SAMPLE_STRUCTURE
    else:
        raise ValueError("%s is not a known run type" %
                         run_type)

    # if its a miseq, there isn't lane information
    if instrument_type == 'miseq':
        header_prefix = ''
        header_suffix = ','
        sample_prefix = ''
        sample_suffix = ','
    elif instrument_type == 'hiseq':
        header_prefix = 'Lane,'
        header_suffix = ''
        sample_prefix = '%(lane)d,'
        sample_suffix = ''
    else:
        raise ValueError("%s is not a recognized instrument type" %
                         instrument_type)

    sample_header = header_prefix + sample_header + header_suffix
    sample_detail_fmt = sample_prefix + sample_detail + sample_suffix

    if run_type == 'Target Gene':
        if instrument_type == 'hiseq':
            lanes = sorted({samp['lane'] for samp in sample_information})
            sample_details = []
            for idx, lane in enumerate(lanes):
                # make a unique run-name on the assumption this is required
                detail = {'lane': lane, 'run_name': run_name + str(idx)}
                sample_details.append(sample_detail_fmt % detail)
        else:
            sample_details = [sample_detail_fmt % {'run_name': run_name}]
    else:
        sample_details = [sample_detail_fmt % samp
                          for samp in sample_information]

    base_sheet = _format_general(run_name, labadmin_id, assay, fwd_cycles,
                                 rev_cycles, pi_name, pi_email,
                                 contact_0_name, contact_0_email,
                                 c1name, c1email,
                                 c2name, c2email)

    full_sheet = "%s%s\n%s\n" % (base_sheet, sample_header,
                                 '\n'.join(sample_details))

    return full_sheet


def _format_general(run_name, labadmin_id, assay, fwd_cycles, rev_cycles,
                    pi_name, pi_email,
                    contact_0_name, contact_0_email,
                    contact_1_name=None, contact_1_email=None,
                    contact_2_name=None, contact_2_email=None):
    """Format the initial parts of a sample sheet

    Parameters
    ----------
    run_name : str
        The name of the run.
    labadmin_id : int
        The ID of the sequencing run as informed by labadmin
    assay : str
        The assay instrument (e.g., Kapa Hyper Plus)
    fwd_cycles : int
        The number of forward cycles
    rev_cycles : int
        The number of reverse cycles
    pi_name : str
        The name of the principle investigator
    pi_email : str
        The email address of the principle investigator
    contact_0_name : str
        The name of an additional contact person
    contact_0_email : str
        The email of an additional contact person
    contact_1_name : str, optional
        The name of an additional contact.
    contact_1_email : str, optional
        The email of an additional contact.
    contact_2_name : str, optional
        The name of an additional contact.
    contact_2_email : str, optional
        The email of an additional contact.

    Raises
    ------
    ValueError
        If any required entries are None or the empty string

    Returns
    -------
    str
        The populated non-sample parts of the sample sheet.
    """
    fmt = {
        'run_name': run_name,
        'assay': assay,
        'date': datetime.datetime.now().strftime("%m/%d/%Y"),
        'fwd_cycles': fwd_cycles,
        'rev_cycles': rev_cycles,
        'labadmin_id': labadmin_id,
        'pi_name': pi_name,
        'pi_email': pi_email,
        'contact_0_name': contact_0_name,
        'contact_0_email': contact_0_email
    }

    optional = {
        'contact_1_name': contact_1_name,
        'contact_1_email': contact_1_email,
        'contact_2_name': contact_2_name,
        'contact_2_email': contact_2_email
    }

    for k, v in fmt.items():
        if v is None or v == '':
            raise ValueError("%s is required")
    fmt.update(optional)

    return SHEET_STRUCTURE % fmt


SHEET_STRUCTURE = """[Header],,,,,,,,,,
IEMFileVersion,4,,,,,,,,,
Investigator Name,%(pi_name)s,,,,PI,%(pi_name)s,%(pi_email)s,,,
Experiment Name,%(run_name)s,,,,Contact,%(contact_0_name)s,%(contact_1_name)s,%(contact_2_name)s,,
Date,%(date)s,,,,,%(contact_0_email)s,%(contact_1_email)s,%(contact_2_email)s,,
Workflow,GenerateFASTQ,,,,,,,,,
Application,FASTQ Only,,,,,,,,,
Assay,%(assay)s,,,,,,,,,
Description,labadmin ID,%(labadmin_id)d,,,,,,,,
Chemistry,Default,,,,,,,,,
,,,,,,,,,,
[Reads],,,,,,,,,,
%(fwd_cycles)d,,,,,,,,,,
%(rev_cycles)d,,,,,,,,,,
,,,,,,,,,,
[Settings],,,,,,,,,,
ReverseComplement,0,,,,,,,,,
,,,,,,,,,,
[Data],,,,,,,,,,
"""  # noqa: E501

DATA_TARGET_GENE_STRUCTURE = "Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,Sample_Project,Description,,"  # noqa: E501

DATA_TARGET_GENE_SAMPLE_STRUCTURE = "%(run_name)s,,,,,NNNNNNNNNNNN,,,,,"

DATA_SHOTGUN_STRUCTURE = "Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,I5_Index_ID,index2,Sample_Project,Description"  # noqa: E501

DATA_SHOTGUN_SAMPLE_STRUCTURE = "%(sample_id)s,,,,%(i7_index_id)s,%(i7_index)s,%(i5_index_id)s,%(i5_index)s,,"  # noqa: E501
