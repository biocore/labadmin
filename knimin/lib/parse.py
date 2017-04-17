def _find_section(lines, label):
    """Find a section, eg [EXCEPTIONS]

    Parameters
    ----------
    lines : list of str
        The data to search over
    label : str
        The section header to search for

    Returns
    -------
    int
        The index of the header
    int
        The index of the first empty line following the section, or the index
        position of the end of the file.

    Raises
    ------
    ValueError
        If the section is not found
    """
    start = -1
    end = len(lines)
    for idx, line in enumerate(lines):
        if line.startswith(label):
            start = idx
            break

    if start == -1:
        raise ValueError('%s section appears to be missing' % label)

    for idx, line in enumerate(lines[start + 1], start):
        if not line:
            end = idx
            break

    return start, end


def parse_echo(data):
    """Parse the Echo output file

    Parameters
    ----------
    data : str
        A str representation of the file

    Returns
    -------
    pd.DataFrame
        A DataFrame composed of the [EXCEPTIONS] section
    pd.DataFrame
        A DataFrame composed of the [DETAILS] section

    Raises
    ------
    ValueError
        If the header is missing
        If the exceptions section is missing
        If the details section is missing
    """
    data = data.splitlines()
    if not data[0].startswith('Run ID'):
        raise ValueError('File header appears to be missing')

    exception_start, exception_end = _find_section(data, '[EXCEPTIONS]')
    details_start, details_end = _find_section(data, '[DETAILS]')
