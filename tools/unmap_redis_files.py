#!/usr/bin/python
from __future__ import print_function

import sys
import os
import re
import datetime
import click
import fadvise


_P_RDB = re.compile('^(?!temp).*\.rdb$')
_P_AOF = re.compile('^(?!temp-rewriteaof).*\.aof$')

def check_aof_or_rdb(filename):
    # RDB is just a snapshot and is not used by redis except at restart.
    if _P_RDB.match(filename):
        return 0
    # AOF is just appendonly format, so unmap is performed only
    # 90% from the beginning of the entire file.
    # But AOF is writes-only, so 100% may be fine.
    # ref: https://github.com/yoshinorim/unmap_mysql_logs
    elif _P_AOF.match(filename):
        return 0.9


def search(dirname):
    data_files = []
    try:
        filenames = os.listdir(dirname)
        for filename in filenames:
            full_filename = os.path.join(dirname, filename)
            if os.path.isdir(full_filename):
                data_files = data_files + search(full_filename)
            else:
                drop_rate = check_aof_or_rdb(filename)
                if drop_rate is not None:
                    data_files.append((full_filename, drop_rate))
    except OSError as e:
        pass
    return data_files


def unmap(filename, offset=0, unmap_len=0):
    f = None
    try:
        if unmap_len < 0:
            raise ValueError('"unmap_len({0})" must be greater than or equal to zero'.format(unmap_len))
        f = fadvise.dontneed(filename, offset=offset, len=unmap_len)
    finally:
        if f: f.close()


def get_file_size(filename):
    return os.stat(filename).st_size


def caculate_unmap_len(file_size, drop_rate):
    return int(file_size * drop_rate)


def logger(*args):
    _now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    msg = ' '.join(map(str, args))
    print('[{0}] {1}'.format(_now, msg))


@click.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--execute', 'execute', is_flag=True,
              help='Default is dry-run mode. Please add this options, '\
                   'if you want to unmap redis data files')
def unmap_redis_files(path, execute):
    '''
        This tool helps unmap redis data files to reduce page cache on server.
    '''
    data_files = search(path)
    log_prefix = ''
    if not execute:
        _unmap = lambda *args: None
        log_prefix = '[DRY-RUN] '
    else:
        _unmap = unmap

    for filename, drop_rate in data_files:
        file_size = get_file_size(filename)
        unmap_len = caculate_unmap_len(file_size, drop_rate)
        _msg = '{0}fileName={1}, dropRate={2}, fileSize={3}, len={4}'.format(
                   log_prefix, filename, drop_rate, file_size, unmap_len)
        logger(_msg)
        _unmap(filename, 0, unmap_len)


if __name__ == '__main__':
    unmap_redis_files()