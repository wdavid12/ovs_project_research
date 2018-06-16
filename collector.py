
import ipfix.ie
import ipfix.reader
import ipfix.message
import ipfix.template

import collections
import socketserver
import argparse

from datetime import datetime as dt

from sys import stdin, stdout, stderr

# IPFIX parameters
OBS_DOMAIN_ID = 2
SAMPLING_TMPL = None

PROTOCOLS = {
        6  : 'tcp: ',
        17 : 'udp: ',
        1  : 'icmp: '
}

# Globals
UPDATE_INTERVAL = 5
CLEAR_STR  = chr(27) + '[2J' + chr(27) + '[H'
start_time = dt.now()
prev_time = dt.now()
flows = collections.OrderedDict()

class FlowCounter():
    def __init__(self):
        self.total_count = 0
        self.count = 0

    def inc(self):
        self.count += 1
        self.total_count += 1

    def reset(self):
        self.count = 0

    def get_count(self):
        return self.count

    def get_total_count(self):
        return self.total_count


class ReaderWithTemplate(ipfix.reader.MessageStreamReader):
    def __init__(self, stream):
        super().__init__(stream)
        self.msg.odid = OBS_DOMAIN_ID
        self.msg.add_template(SAMPLING_TMPL, export=False)
        self.msg.accepted_tids.add((OBS_DOMAIN_ID, SAMPLING_TMPL.tid))


def draw_screen(seconds):
    global start_time, flows
    print(CLEAR_STR)
    now = dt.now()
    elapsed = now - start_time
    print('[ %s ][ Elapsed: %-10d seconds ][ %s ]' % (
        'IPFIX Flows',
        elapsed.seconds,
        now.isoformat(timespec='seconds', sep=' ')))
    print()
    print("%-40s%-30s%-20s\n" % ('Flow','Rate (packets/sec)','Total Count'))
    for k,v in flows.items():
        rate = v.get_count() / seconds
        print("%-40s%5f%20d" % (k, rate, v.get_total_count()))
        v.reset()


def parse_args():
    parser = argparse.ArgumentParser(description="Display IPFIX flows")
    parser.add_argument('--bind', '-b', metavar="bind", nargs="?",
                        default="", help="address to bind to as Collector (default all)")
    parser.add_argument('--port', '-p', metavar="port", nargs="?", type=int,
                        default="4739", help="port to bind to as Collector (default 4739)")
    return parser.parse_args()


def init_ipfix():
    global SAMPLING_TMPL
    ipfix.ie.use_iana_default()
    ipfix.ie.use_5103_default()
    tmpl = ipfix.template.from_ielist(376,
            ipfix.ie.spec_list(("sourceMacAddress",
                                "destinationMacAddress",
                                "sourceIPv4Address",
                                "destinationIPv4Address",
                                "protocolIdentifier",
                                "sourceTransportPort",
                                "destinationTransportPort")))
    SAMPLING_TMPL = tmpl


def format_record(rec):
    key = []
    transport = False
    proto = rec["protocolIdentifier"]
    if proto in [6,17]:
        transport = True

    if proto in PROTOCOLS:
        key.append(PROTOCOLS[proto])
    else:
        key.append('unknown: ')
    key.append(str(rec["sourceIPv4Address"]))
    if transport:
        key.append(":"+str(rec["sourceTransportPort"]))

    key.append(' => ')
    key.append(str(rec["destinationIPv4Address"]))
    if transport:
        key.append(":"+str(rec["destinationTransportPort"]))

    return ''.join(key)


def process_data(instream):
    global prev_time, flows

    r = ReaderWithTemplate(instream)

    for rec in r.namedict_iterator():
        key = format_record(rec)
        if key not in flows:
            flows[key] = FlowCounter()
        flows[key].inc()

    duration = dt.now() - prev_time
    if duration.seconds > UPDATE_INTERVAL:
        prev_time = dt.now()
        draw_screen(duration.seconds)


class UdpIPFIXHandler(socketserver.DatagramRequestHandler):
    def handle(self):
        process_data(self.rfile)


if __name__ == "__main__":

    # get args
    args = parse_args()

    # initialize information model
    init_ipfix()

    draw_screen(60)

    ss = socketserver.UDPServer((args.bind, args.port), UdpIPFIXHandler)
    ss.serve_forever()

