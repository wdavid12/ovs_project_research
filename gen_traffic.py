from scapy.all import *

DESTINATION = '192.168.1.22'

# 2 packets per second
INTERVAL = 0.5

pkts = IP(dst=DESTINATION)/UDP(dport=[10222,10223,10224])

print('summary of packets:')
for p in pkts:
    print(p.summary())

send(pkts, inter=0.5, loop=1)
