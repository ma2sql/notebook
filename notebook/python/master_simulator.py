import random


class Server:
    def __init__(self, ip, port, readonly, master_ip):
        self._ip = ip
        self._port = port
        self._readonly = readonly
        self._master_ip = master_ip
        self._slaves = list()

    @property
    def master_ip(self):
        return self._master_ip

    @property
    def ip(self):
        return self._ip

    @property
    def port(self):
        return self._port

    @property
    def readonly(self):
        return self._readonly

    @property
    def slaves(self):
        return self._slaves

    @slaves.setter
    def slaves(self, slave_list):
        self._slaves = slave_list
        
    def slaves_string(self):
        return self._slaves
        
    def __str__(self):
        return '{}:{}'.format(self._ip, self._port)


class Servers:
    def __init__(self):
        self._servers = []

    def get_server(self, ip):
        for server in self._servers:
            if server.ip == ip:
                return server
        return None
        
    def get_random_server(self):
        return self._servers[random.randint(0, self.size() - 1)]

    def server_factory(self, ip, port, readonly, master):
        server = Server(ip, port, readonly, master)
        self._servers.append(server)
        self.update_slaves()
        return server

    def update_slaves(self):
        for server in self._servers:
            new_slaves = filter(lambda x: x.master_ip == server.ip, self._servers)
            server.slaves = new_slaves

    def size(self):
        return len(self._servers)


def find_master(server, pre_server, servers, idx=1):
    print '({}) ip={}, slaves={}'.format(idx, server, len(server.slaves))
    if server.master_ip == None:
        return [server]
    elif pre_server is not None and server.master_ip == pre_server.ip:
        return [server, pre_server]
    else:
        return find_master(servers.get_server(server.master_ip), server, servers, idx+1)


def elect_master(candidates):
    elected_master = filter(lambda x: len(x.slaves) > 1 and not x.readonly, candidates)
    if elected_master:
        return elected_master[0]
    else:
        # draw
        writable_masters = filter(lambda x: not x.readonly, candidates)
        return writable_masters[0] if writable_masters else None

        
if __name__ == '__main__':
    servers = Servers()
    servers.server_factory('10.10.10.6', 20306, True, '10.10.10.5')
    servers.server_factory('10.10.10.5', 20306, True, '10.10.10.3')
    servers.server_factory('10.10.10.1', 20306, False, '10.10.10.2')
    servers.server_factory('10.10.10.2', 20306, True, '10.10.10.1')
    servers.server_factory('10.10.10.3', 20306, True,  '10.10.10.1')
    servers.server_factory('10.10.10.4', 20306, True,  '10.10.10.1')

    start_server = servers.get_random_server()
    master_candidates = find_master(start_server, None, servers)

    print 'Candidates: {}'.format(map(lambda x: (x.ip, x.port, x.readonly, len(x.slaves)), master_candidates))
    print 'Elected: {}'.format(elect_master(master_candidates))

