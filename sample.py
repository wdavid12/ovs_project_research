import requests, itertools, sys

API_URL= 'http://localhost:8080'
DUMP_FMT = '| %-3s | %-4s | %-35s| %-35s|'
DUMP_LEN = 88

def get_switch():
    r = requests.get(API_URL+'/stats/switches')
    r.raise_for_status()
    switches = r.json()

    if len(switches) == 0:
        sys.exit("Error: no switches found. Exiting")

    for s in r.json():
        print("[-] Found Switch: %d" % s)

    switch = switches[0]
    print("[-] Assuming switch is %d" % switch)
    return str(switch)

switch = get_switch()

class Protocol:
    TCP = 1
    UDP = 2

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
        sample_ip <ip> <prob> <dst port> - start sampling from ip
        stop_ip <ip> <prob> <dst port>   - stop sampling from ip
    '''
    print(help_str)

def dump_cmd(args):
    print('[-] Dumping OpenFlow Table')
    r = requests.get(API_URL+'/stats/flow/' + switch)
    r.raise_for_status()
    result = r.json()
    if switch not in result:
        print('Flows for switch not found')
        return
    flow_entries = result[switch]
    print('-'*DUMP_LEN)
    print(DUMP_FMT % ('num','prio', 'match rules', 'actions'))
    for i, e in enumerate(flow_entries):
        print_flow_entry(i,e)
    print('-'*DUMP_LEN)

def sample_ip_path(args,path):
    if len(args) != 3:
        print('Expected 3 argument')
        return

    match = {
        'eth_type': 0x0800,  # IP
        'ipv4_src': args[0]
    }

    entry = construct_flow_entry(match, int(args[1]), int(args[2]))

    requests.post(API_URL+path, json=entry)

def sample_ip_cmd(args):
    sample_ip_path(args, '/stats/flowentry/add')
    print('[-] Sampling src ip %s' % args[0])

def stop_ip_cmd(args):
    sample_ip_path(args, '/stats/flowentry/delete')
    print('[-] Stopping sampling from ip %s' % args[0])

cmds = {
        'help': help_cmd,
        'dump': dump_cmd,
        'sample_ip': sample_ip_cmd,
        'stop_ip': stop_ip_cmd
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
            print('unknown command: %s' % cmd)
            continue

        cmds[cmd](args[1:])

if __name__ == '__main__':
    main()

