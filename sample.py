import requests, itertools, sys

# main options
API_URL= 'http://localhost:8080'
ROUTING_TABLE = {
    '10.0.0.1': 2,
    '10.0.0.2': 1,
}

# for printing
DUMP_FMT = '| %-3s | %-4s | %-35s| %-35s|'
DUMP_LEN = 88

# probability does not matter for deletion
DUMMY = '1337'

def get_switch():
    r = requests.get(API_URL+'/stats/switches')
    r.raise_for_status()
    switches = r.json()

    if len(switches) == 0:
        sys.exit("[!] Error: no switches found. Exiting")

    for s in r.json():
        print("[-] Found Switch: %d" % s)

    switch = switches[0]
    print("[-] Assuming switch is %d" % switch)
    return str(switch)

switch = get_switch()

class Protocol:
    TCP = 6
    UDP = 17
    ICMP = 1

def construct_flow_entry(match, probability, output):
    template = {
        "dpid": switch,
        "priority": 10,
        "table_id": 0,
        "cookie": 0,
        "flags": 0,
        "hard_timeout": 0,
        "idle_timeout": 0,
    }

    sample_action = {
        "collector_set_id": 2,
        "experimenter": 8992,
        "obs_domain_id": 2,
        "obs_point_id": 3,
        "probability": probability,
        "subtype": 29,
        "type": "EXPERIMENTER"
    }
    output_action = {
        "port": output,
        "type": "OUTPUT"
    }

    template['match'] = match
    template['instructions'] = [{
            'type': 'APPLY_ACTIONS',
            'actions': [sample_action, output_action]
            # 'actions': [output_action]
    }]

    return template

def print_flow_entry(idx, entry):
    print('-'*DUMP_LEN)
    idx = [str(idx)]
    prio = [entry['priority']]

    matches = entry['match']
    matches = ("%s: %s" % (k,v) for k,v in matches.items())

    instructions = entry['instructions']

    actions_strs = []
    actions = None
    for inst in instructions:
        if inst['type'] == 'APPLY_ACTIONS':
            actions = inst['actions']

    if actions is not None:
        for act in actions:
            if act['type'] == 'OUTPUT':
                actions_strs.append('OUTPUT to port %d' % act['port'])
            elif act['type'] == 'EXPERIMENTER' and act['experimenter'] == 8992:
                actions_strs.append('SAMPLE with prob=%d' % act['probability'])
            else:
                actions_strs.append(act['type'])

    for a,b,c,d in itertools.zip_longest(idx,prio, matches,actions_strs,fillvalue=''):
        print(DUMP_FMT % (a,b,c,d))

def help_cmd(args):
    help_str = '''
    Available commands:
        help - print help message
        dump - dump OpenFlow tables
        exit - exit program
        sample_src_ip <ip> <prob> - start sampling from ip
        stop_src_ip   <ip>        - stop sampling from ip
        sample_icmp <ip> <prob> - start sampling icmp from ip
        stop_icmp   <ip>        - stop sampling icmp from ip
        sample_udp <ip> <port> <prob> - start sampling udp from ip
                                        port is the destination port
        stop_udp   <ip> <port>        - stop sampling udp from ip
        sample_tcp <ip> <port> <prob> - start sampling tcp from ip
                                        port is the destination port
        stop_tcp   <ip> <port>        - stop sampling tcp from ip
    '''
    print(help_str)

def dump_cmd(args):
    print('[-] Dumping OpenFlow Tables')
    r = requests.get(API_URL+'/stats/flow/' + switch)
    r.raise_for_status()
    result = r.json()
    if switch not in result:
        print('[!] Flows for switch not found')
        return
    flow_entries = result[switch]
    print('-'*DUMP_LEN)
    print(DUMP_FMT % ('num','prio', 'match rules', 'actions'))
    for i, e in enumerate(flow_entries):
        print_flow_entry(i,e)
    print('-'*DUMP_LEN)

def valid_port(port):
    if port < 1 or port > 65535:
        print("[!] Invalid port %d. sampling aborted" % port)
        return False
    return True

def valid_ip(addr):
    if addr not in ROUTING_TABLE:
        print('[!] ip %s not in routing table. sampling aborted' % addr)
        return False
    return True

def valid_probability(prob):
    if prob < 0 or prob > 65535:
        print('[!] invalid probability %d. sampling aborted' % prob)
        return False
    return True

def openflow_impl(match, prob, remove = False):
    if not valid_ip(match['ipv4_src']):
        return

    if not valid_probability(prob):
        return

    dst_port = ROUTING_TABLE[match['ipv4_src']]

    entry = construct_flow_entry(match, prob, dst_port)

    path = '/stats/flowentry/add'
    if remove:
        path = '/stats/flowentry/delete_strict'

    requests.post(API_URL+path, json=entry)

def sample_src_ip_impl(args, remove = False):
    match = {
        'eth_type': 0x0800,  # IP
        'ipv4_src': args[0]
    }
    openflow_impl(match, int(args[1]), remove)

def sample_tcp_impl(args, remove = False):
    if not valid_port(int(args[1])):
        return

    match = {
        'eth_type': 0x0800,  # IP
        'ipv4_src': args[0],
        'ip_proto': Protocol.TCP,
        'tcp_dst': int(args[1])
    }
    openflow_impl(match, int(args[2]), remove)

def sample_udp_impl(args, remove = False):
    if not valid_port(int(args[1])):
        return

    match = {
        'eth_type': 0x0800,  # IP
        'ipv4_src': args[0],
        'ip_proto': Protocol.UDP,
        'udp_dst': int(args[1])
    }
    openflow_impl(match, int(args[2]), remove)

def sample_icmp_impl(args, remove = False):
    match = {
        'eth_type': 0x0800,  # IP
        'ipv4_src': args[0],
        'ip_proto': Protocol.ICMP,
    }
    openflow_impl(match, int(args[1]), remove)

def sample_src_ip_cmd(args):
    print('[-] Sampling src ip %s' % args[0])
    sample_src_ip_impl(args)

def stop_src_ip_cmd(args):
    args.append(DUMMY)
    print('[-] Stopping sampling from ip %s' % args[0])
    sample_src_ip_impl(args, True)

def sample_icmp_cmd(args):
    print('[-] Sampling icmp src ip %s' % args[0])
    sample_icmp_impl(args)

def stop_icmp_cmd(args):
    args.append(DUMMY)
    print('[-] Stopping sampling icmp from ip %s' % args[0])
    sample_icmp_impl(args, True)

def sample_tcp_cmd(args):
    print('[-] Sampling tcp from ip %s to port %s' % (args[0], args[1]))
    sample_tcp_impl(args)

def stop_tcp_cmd(args):
    args.append(DUMMY)
    print('[-] Stopping sampling tcp from ip %s to port %s' % (args[0], args[1]))
    sample_tcp_impl(args, True)

def sample_udp_cmd(args):
    print('[-] Sampling udp from ip %s to port %s' % (args[0], args[1]))
    sample_udp_impl(args)

def stop_udp_cmd(args):
    args.append(DUMMY)
    print('[-] Stopping sampling udp from ip %s to port %s' % (args[0], args[1]))
    sample_udp_impl(args, True)

cmds = {
        'help': (help_cmd,0),
        'dump': (dump_cmd,0),
        'sample_src_ip': (sample_src_ip_cmd,2),
        'stop_src_ip': (stop_src_ip_cmd,1),
        'sample_icmp': (sample_icmp_cmd,2),
        'stop_icmp': (stop_icmp_cmd,1),
        'sample_udp': (sample_udp_cmd,3),
        'stop_udp': (stop_udp_cmd,2),
        'sample_tcp': (sample_tcp_cmd,3),
        'stop_tcp': (stop_tcp_cmd,2),
        }

def main():
    while True:
        cmdline = input('Enter command: ')
        args = cmdline.split()
        if len(args) == 0:
            continue
        cmd = args[0]

        if cmd == 'exit':
            sys.exit('bye')

        if not cmd in cmds:
            print('[!] unknown command: %s' % cmd)
            continue

        func, numargs = cmds[cmd]
        if len(args[1:]) != numargs:
            print('[!] Wrong number of arguments: expected %d' % numargs)
            continue

        func(args[1:])

if __name__ == '__main__':
    main()

