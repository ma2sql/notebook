import redis
import sys
from collections import defaultdict
from operator import itemgetter

r = None

TYPE_META = {
    'string': ('STRLEN', 0, 'bytes'),
    'list': ('LLEN', 1, 'items'),
    'set': ('SCARD', 2, 'members'),
    'hash': ('HLEN', 3, 'fields'),
    'zset': ('ZCARD', 4, 'members'),
    'stream': ('XLEN', 5, 'entries'),
    'other': (None, 6, '?'),
}

def get_keys_types(keys):
    result = None
    with r.pipeline(transaction=False) as p:
        for k in keys:
            p.type(k)
        result = p.execute()
    return result


def get_keys_sizes_legacy(keys, types, **kwargs):
    result = None
    with r.pipeline(transaction=False) as p:
        for k, t in zip(keys, types):
            cmd, *_ = TYPE_META[t]
            p.execute_command(cmd, k)
        result = p.execute()
    return result


def get_keys_sizes_memory_command(keys, types, **kwargs):
    result = None
    memory_samples = kwargs.get('memkeys_samples')
    with r.pipeline(transaction=False) as p:
        for k in keys:
            p.memory_usage(k, samples=memory_samples)
        result = p.execute()
    return result



def scan_iter_chunk(count=None, match=None):
    keys = []
    for k in r.scan_iter(count=count, match=match):
        keys.append(k)
        if len(keys) == 100:
            yield keys
            keys = []
    yield keys


def find_big_keys(memkeys, memkeys_samples=None, interval=None):
    redis_info = r.info()
    cluster_enabled = (redis_info['cluster_enabled'] == 1 
                       if redis_info.get('cluster_enabled') 
                       else False)
    role = redis_info['role']
    if cluster_enabled and role == 'slave':
        r.readonly()
        
    redis_major_version = int(redis_info['redis_version'].split('.')[0])
    if not memkeys or redis_major_version < 4:
        get_keys_sizes = get_keys_sizes_legacy
    else:
        get_keys_sizes = get_keys_sizes_memory_command

    total_keys = r.dbsize()

    print('\n'\
          '# Scanning the entire keyspace to find biggest keys as well as\n'\
          '# average sizes per key type.  You can use -i 0.1 to sleep 0.1 sec\n'\
          '# per 100 SCAN commands (not usually needed).\n')

    sampled = 0
    totlen = 0
    keys = []

    summary = {}
    for key_type, v in TYPE_META.items():
        cmd, sort_key, unit = v
        summary[key_type] = {
            'sort_key': sort_key,
            'unit': unit,
            'biggest': 0,
            'count': 0,
            'totalsize': 0,
            'biggest_key': None
        }
    
    for keys in scan_iter_chunk(count=100):
        pct = (float(sampled) / total_keys) * 100

        types = get_keys_types(keys)
        sizes = get_keys_sizes(keys, types, samples=memkeys_samples)
        for i, k in enumerate(keys):
            key_type = types[i]
            if not key_type:
                continue

            key_size = sizes[i]

            sampled += 1
            totlen += len(k)
            summary[key_type]['totalsize'] += key_size
            summary[key_type]['count'] += 1

            if summary[key_type]['biggest'] < key_size:
                unit = 'bytes' if memkeys else TYPE_META[key_type][2]
                print('''[{:05.2f}%] Biggest {:<6} found so far '{}' with {} {}'''.format(
                    pct, key_type, k, key_size, unit))
                summary[key_type]['biggest_key'] = k
                summary[key_type]['biggest'] = key_size
        
            if sampled % 1000000 == 0:
                print('[{:05.2f}%] Sampled {} keys so far'.format(pct, sampled))


    if interval and (sampled % 100 == 0):
        time.sleep(interval/1000000.0)

    print('\n-------- summary -------\n')
    print('Sampled {} keys in the keyspace!'.format(sampled))
    print('Total key length in bytes is {} (avg len {:.2f})\n'.format(
          totlen, float(totlen) / sampled if totlen else 0))

    for key_type, d in sorted(summary.items(), key=lambda k: k[1]['sort_key']):
        if d['biggest']:
            unit = 'bytes' if memkeys else TYPE_META[key_type][2]
            print('''Biggest {:>6} found '{}' has {} {}'''.format(key_type, d['biggest_key'], d['biggest'], unit))
    
    print()
    for key_type, d in sorted(summary.items(), key=lambda k: k[1]['sort_key']):
        unit = 'bytes' if memkeys else d['unit']
        print('{} {}s with {} {} ({:05.2f}% of keys, avg size {:.2f})'.format(
            d['count'], key_type, d['totalsize'], unit, 
            (float(d['count']) / sampled) * 100 if sampled else 0,
            float(d['totalsize']) / d['count'] if d['count'] else 0))