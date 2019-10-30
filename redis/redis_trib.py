'''
{
    "10.233.213.248:11300@21300": {
        "node_id": "6da7a15de1d69786919b6641c19ebd0194e99bf9",
        "flags": "slave",
        "master_id": "e5c2eae89ea8c9c8f19bb0adc88f996e416f5454",
        "last_ping_sent": "0",
        "last_pong_rcvd": "1572408954743",
        "epoch": "3",
        "slots": [],
        "connected": true
    },
    "10.233.213.247:11300@21300": {
        "node_id": "e5c2eae89ea8c9c8f19bb0adc88f996e416f5454",
        "flags": "master",
        "master_id": "-",
        "last_ping_sent": "0",
        "last_pong_rcvd": "1572408952000",
        "epoch": "3",
        "slots": [
            [
                "10923",
                "16383"
            ]
        ],
        "connected": true
    },
    "10.233.213.249:11300@21300": {
        "node_id": "bc401b99221a31dd546bbc133d9d1e8eae00aefa",
        "flags": "myself,master",
        "master_id": "-",
        "last_ping_sent": "0",
        "last_pong_rcvd": "1572408953000",
        "epoch": "9",
        "slots": [
            [
                "0",
                "5460"
            ],
            [
                "[5461",
                "<",
                "b35b55daf26e84acdf17fed30d46ca97ccdd9169]"
            ]
        ],
        "connected": true
    },
    "10.233.213.246:11300@21300": {
        "node_id": "d2ae009107b56802ebcce6a1610282238323856e",
        "flags": "slave",
        "master_id": "bc401b99221a31dd546bbc133d9d1e8eae00aefa",
        "last_ping_sent": "0",
        "last_pong_rcvd": "1572408954000",
        "epoch": "9",
        "slots": [],
        "connected": true
    },
    "10.233.213.244:11300@21300": {
        "node_id": "dc39f50e925e398eb45c6435fd3b747c5558e2a4",
        "flags": "slave",
        "master_id": "b35b55daf26e84acdf17fed30d46ca97ccdd9169",
        "last_ping_sent": "0",
        "last_pong_rcvd": "1572408955000",
        "epoch": "6",
        "slots": [],
        "connected": true
    },
    "10.233.213.245:11300@21300": {
        "node_id": "b35b55daf26e84acdf17fed30d46ca97ccdd9169",
        "flags": "master",
        "master_id": "-",
        "last_ping_sent": "0",
        "last_pong_rcvd": "1572408955744",
        "epoch": "6",
        "slots": [
            [
                "5461",
                "10922"
            ]
        ],
        "connected": true
    }
}
'''
import redis
import sys

MIGREATE_DEFAULT_TIMEOUT = 60000

class ClusterNode:
    def __init__(self, addr, password=None):
        s = addr.split('@')[0].split(':')
        if len(s) < 2:
           puts "Invalid IP or Port (given as #{addr}) - use IP:Port format"
           sys.exit(1)

        port = s[-1] # removes port from split array
        ip = s[:-1].join(":") # if s.length > 1 here, it's IPv6, so restore address

        self._r = None
        self._password = password
        self._info = {
            'host': ip,
            'port': port,
            'slots': {},
            'importing': {},
            'migrating': {}
        }
        self._dirty = False # True if we need to flush slots info into node.
        self._friends = []


    def connect(self, abort=False, force=False):
        if self._r or not force:
            return

        try:
            self._r = StrictRedis(host=self._info['host'], 
                                  port=self._info['port'], 
                                  password=self._password,
                                  timeout=60)
            self._r.ping()
        except redis.RedisError:
            print('''[ERR] Sorry, can't connect to node {}]'''.format(self))
            self._r = None
            if abort:
                sys.exit(1)


    def assert_cluster(self):
        info = self._r.info('cluster')
        if info.get('cluster_enabled') != 1:
            print('''[ERR] Node {} is not configured as a cluster node.'''.format(self))
            sys.exit(1)


    def assert_empty(self):
        cluster_info = self._r.cluster('info')
        info = self._r.info('keyspace')
        if (int(cluster_info['cluster_known_nodes']) != 6
            or info.get('db0')):
            print('[ERR] Node {} is not empty. '\
                  'Either the node already knows other nodes'\
                  ' (check with CLUSTER NODES) or '\
                  'contains some key in database 0.'.format(self))
            sys.exit(1)


class RedisTrib:
    def __init__(self):
        self._nodes = []
        self._fix = False
        self._errors = []
        self._timeout = MIGREATE_DEFAULT_TIMEOUT
    

    def create_cluster(self, addrs, **opt):
        replicas = opt.get('replicas') or 0

        print('>>> Creating cluster')
        for addr in addrs:
            node = ClusterNode(addr)
            node.connect(abort=True)
            node.assert_cluster()
            node.load_info()
            node.assert_empty()
            nodes.append(node)


    def _add_node(self, node):
        self._nodes.append(node)

    
    def _



def create_cluster_cmd(addrs, **opt):
    replicas = opt.get('replicas') or 0
    nodes = []

    print('>>> Creating cluster')
    for addr in addrs:
        node = ClusterNode(addr)
        node.connect(abort=True)
        node.assert_cluster()
        node.load_info()
        node.assert_empty()
        nodes.append(node)
    
    check_create_parameters()
    alloc_slots()
    show_nodes()
    yes_or_die()
    flush_nodes_config()
    assign_config_epoch()
    join_cluster()
    time.sleep(1)
    wait_cluster_join()
    flush_nodes_config()
    reset_nodes()
    load_cluster_info_from_node(addrs[0])
    check_cluster()
