import time
import threading
import threading
import configparser
import argparse
import random

from xmlrpc.server import SimpleXMLRPCServer
import xmlrpc.client

ELECTION_TIMEOUT = 5

class RaftConnectionDetails():
    def __init__(self, host, port, name):
        self.name = name
        self.host = host
        self.port = port

class Raft:
    def __init__(self, user_con_details, remote_con_details):
            self.name = user_con_details.name
            self.log = []
            self.x = 0
            self.num_of_servers = len(remote_con_details)+1
            self.is_election_time = False
            self.state = "follower"
            self.current_term = 0
            print(f"hosting on {user_con_details.host, int(user_con_details.port)}")
            self.server = SimpleXMLRPCServer((user_con_details.host, int(user_con_details.port)))
            self.server.register_function(self.append_entries,"append_entries")
            self.server.register_function(self.request_vote,"request_vote")
            self.server.register_function(self.set_x,"set_x")
            self.server.register_function(self.get_x,"get_x")
            self.manager = threading.Thread(target=self.run)
            # we randomise to not trigger all nodes creating election at same time...
            delay = random.uniform(1,10)
            self.trigger_election = threading.Timer(delay, self.create_election)
            self.trigger_election.start()
            self.heartbeats = threading.Thread(target=self.heartbeats)
            self.heartbeats.start()
            self.commit_index = 0

            self.clients = []

            for remote_con in remote_con_details:
                print(f"connecting to {remote_con.host}:{remote_con.port}")
                proxy = xmlrpc.client.ServerProxy(f"http://{remote_con.host}:{remote_con.port}/")
                self.clients.append(proxy)

            self.manager.start()
            self.server.serve_forever()

    def heartbeats(self):
        while True:
            if self.state == "leader":
                # telling everyone we are the captain of this distributed ship :pirate_ship:
                for proxy in self.clients:
                    try:
                        proxy_term, proxy_vote_granted = proxy.append_entries(self.current_term,0,0,0, [], 0)
                    except:
                        # todo: what to do
                        continue
            time.sleep(2)


    def create_election(self):
        print("MAGA TIME")
        self.state = "candidate"
        # votes for itself so start at 1
        number_of_votes = 1
        majority_votes_required = self.num_of_servers/2
        for proxy in self.clients:
            try:
                proxy_term, proxy_vote_granted = proxy.request_vote(self.current_term,0,0,0)
                number_of_votes += int(proxy_vote_granted)
            except:
                # todo: what to do
                continue
        if number_of_votes >= majority_votes_required:
            # We become leader and state our leadership by sending empty append_entries
            print(f"{self.name} is the leader!!!! {number_of_votes} / {majority_votes_required}")
            self.state = "leader"
            self.current_term += 1
            for proxy in self.clients:
                try:
                    proxy_term, proxy_vote_granted = proxy.append_entries(self.current_term,0,0,0, [], 0)
                except:
                    # todo: what to do
                    continue
        else:
            print(f"{self.name} is the leader :(( {number_of_votes} / {majority_votes_required}")

    def run(self):
        while True:
            time.sleep(5)

    def append_entries(self,term: int, leader_id: int, prev_log_index: int, prev_log_term: int, entries: list[str], leader_commit: int) -> (int, bool): # (term, success)
        if self.state == "candidiate" and term >= self.current_term:
            # todo: kill election
            ...
        if self.state == "candidiate" and term < self.current_term:
            # todo: reject and go on
            ...
        if self.state == "follower":
            # leader has told us he is alive so reset connection timeout (with a bit of jitter to make life easier)
            self.trigger_election.cancel()
            self.trigger_election = threading.Timer(ELECTION_TIMEOUT+random.uniform(0,5), self.create_election)
            self.trigger_election.start()
        if self.state == "leader":
            # wtf is this person doing were aren't byznatine fault tolerant???? lets die
            sys.exit(-1)
        if len(entries) >= 1:
            #lets process updates from master
            # here we need to do checks to ensure log term is ok
            # and commit index is also ok
            print("append entries found")
            for x in entries:
                self.log.append(x)
                self.x = x
        if term < self.current_term:
            # he is an old leader! gtfo
            return (self.current_term, False)
        return (self.current_term,True)
    
    def request_vote(self,term: int, candidate_id: int, last_log_index: int, last_log_term: int) -> (int, bool): #(term, vote granted)
        print("request_vote")
        return (0,True)
    
    def set_x(self, new_x):
        if self.state == "leader":
            # commit to log
            self.log.append(new_x)
            self.x = new_x
            self.notify_followers_of_update()
        else:
            # cry as i am not leader sadge
            ...

    def notify_followers_of_update(self):
        all_nodes_commit_counter = 0
        for proxy in self.clients:
            try:
                proxy_term, can_commit = proxy.append_entries(self.current_term,self.name,len(self.log)-1,self.current_term-1, [self.x], len(self.log)-1)
                all_nodes_commit_counter += int(can_commit)
            except Exception as e:
                # todo: what to do
                continue
        majority_votes_required = self.num_of_servers/2
        print(f"sending commit to followers. got {all_nodes_commit_counter}/{majority_votes_required}")
        if all_nodes_commit_counter > majority_votes_required:
            print("enought clients have allowed potential commit lets commit")
            # we have been given the A ok! lets commit
            all_nodes_commit_counter = 0
            for proxy in self.clients:
                try:
                    proxy_term, can_commit = proxy.append_entries(self.current_term,self.name,len(self.log)-1,self.current_term-1, [self.x], len(self.log))
                    all_nodes_commit_counter += int(can_commit)
                except Exception as e:
                    # todo: what to do
                    continue
            if all_nodes_commit_counter > majority_votes_required:
                # practically two phase commit
                print("majority commits acked")
                self.commit_index = len(self.log)

    def get_x(self):
        # in theory we can return here but we don't have strict consistency so
        # for the theory of this system lets not do it...
        if self.state == "leader" and self.commit_index >= len(self.log):
            return self.x
        else:
            return None

def read_config(file_path, user) -> (RaftConnectionDetails, list[RaftConnectionDetails]):
    config = configparser.ConfigParser()
    config.read(file_path)
    user_con = None
    remote_con = []

    for section in config.sections():
        if str(section) == user:
            print(f'user section: {section}')
            user_con = RaftConnectionDetails(config[section]["host"], config[section]["port"], config[section]["name"])
        else:
            print(f'remote section: {section}')
            remote_con.append(RaftConnectionDetails(config[section]["host"], config[section]["port"], config[section]["name"]))
    return (user_con, remote_con)

def main():
    print("starting raft")
    parser = argparse.ArgumentParser(description='goose-raft')
    parser.add_argument('config', metavar='N', type=str, nargs=1, help='location of config_file')
    parser.add_argument('system', metavar='N', type=str, nargs=1, help='location of config_file')
    args = parser.parse_args()

    user_con_details, remote_con_details = read_config(args.config, f"{args.system[0]}")

    raft = Raft(user_con_details, remote_con_details)

if __name__ == "__main__":
    main()

# The problems with this system
# - logs aren't persistent
# - log snapshots
# - rebuilding logs generally
