from __future__ import print_function

import os
import sys
import click
from rdbtools import RdbParser, MemoryCallback, PrintAllKeys
from rdbtools.memprofiler import codecs, heappush


class MyPrintAllKeys(PrintAllKeys):
    def __init__(self, out, bytes, largest):
        super(MyPrintAllKeys, self).__init__(out, bytes, largest)

    def next_record(self, record):
        if record.key is None:
            return  # some records are not keys (e.g. dict)
        if self._largest is None:
            if self._bytes is None or record.bytes >= int(self._bytes):
                rec_str = "%d,%s,%s,%d,%s,%d,%d,%s\n" % (
                    record.database, record.type, record.key.encode('utf-8').hex(), record.bytes, record.encoding, record.size,
                    record.len_largest_element,
                    record.expiry.isoformat() if record.expiry else '')
                self._out.write(codecs.encode(rec_str, 'latin-1'))
        else:
            heappush(self._heap, (record.bytes, record))



@click.command()
@click.argument('dump_file')
@click.option('--output-file', '-f', help='output file')
@click.option('--bytes', '-b', type=int, default=None,
              help='Limit memory output to keys greater to or equal to this value (in bytes)')
@click.option('--largest','-l', type=int, default=None,
              help='Limit memory output to only the top N keys (by size)')
def memory_profiler(dump_file, bytes, largest, output_file=None):
    out_file_obj = None
    try:
        if output_file:
            out_file_obj = open(output_file, "wb")
        else:
            # Prefer not to depend on Python stdout implementation for writing binary.
            out_file_obj = os.fdopen(sys.stdout.fileno(), 'wb')

        callback = MemoryCallback(MyPrintAllKeys(out_file_obj, bytes, largest),
                                                 64, string_escape=None)
        parser = RdbParser(callback, filters={})
        parser.parse(dump_file)

    finally:
        if output_file and out_file_obj is not None:
            out_file_obj.close()


if __name__ == '__main__':
    memory_profiler()