# http://stackoverflow.com/a/19722365
import zipfile

try:
    from cStringIO import StringIO
except ImportError:
    from io import BytesIO as StringIO


class InMemoryZip(object):
    def __init__(self):
        # Create the in-memory file-like object
        self.in_memory_data = StringIO()
        # Create the in-memory zipfile
        self.in_memory_zip = zipfile.ZipFile(
            self.in_memory_data, "w", zipfile.ZIP_DEFLATED, False)
        self.in_memory_zip.debug = 3

    def append(self, filename_in_zip, file_contents):
        '''Appends a file with name filename_in_zip and contents of
        file_contents to the in-memory zip.

        Parameters
        ----------
        filename_in_zip : str
            Filename of zip file.
        file_contents : str
            Contents to be written into file.
        '''
        self.in_memory_zip.writestr(filename_in_zip, file_contents)
        return self   # so you can daisy-chain

    def writetofile(self, filename):
        '''Writes the in-memory zip to a file.

        Parameters
        ----------
        filename : str
           Name of the output zip file.
        '''
        # Mark the files as having been created on Windows so that
        # Unix permissions are not inferred as 0000
        for zfile in self.in_memory_zip.filelist:
            zfile.create_system = 0
        self.in_memory_zip.close()
        with open(filename, 'wb') as f:
            f.write(self.in_memory_data.getvalue())

    def write_to_buffer(self):
        """ Closes the buffer and returns the binary content.

        Returns
        -------
        str : binary content of the zipped buffer.

        See Also
        --------
        io.BytesIO
        """
        self.in_memory_zip.close()
        return self.in_memory_data.getvalue()

if __name__ == "__main__":
    # Run a test
    imz = InMemoryZip()
    imz.append("test.txt", "Another test").append("test2.txt", "Still another")
    imz.writetofile("test.zip")
