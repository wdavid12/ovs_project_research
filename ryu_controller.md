# Introduction
Ryu is a python library that allows us to create SDN controllers while working
at relatively high level.

## Enabling Sampling on Demand
The OVS project has extended the OpenFlow protocol with new types of actions,
one of which is the `sample()` action that will allow us to activate sampling
per flow.

Luckily, Ryu has implemented these extensions for us. within Ryu, these are
called "Nicira Extension Structures". (Nicira was/is the company behind
OVS). You can follow [this link](ryu.readthedocs.io/en/latest/nicira_ext_ref.html)
for more information.

The structure we are intersted in is
```
ryu.ofproto.ofproto_v1_3_parser.NXActionSample(probablity, collector_set_id=0,
				obs_domain_id=0, obs_point_id=0, type_=None,
				len_=None, experimenter=None,subtype=None)
```
from the ryu documentation:
> This action samples packets and sends one sample for every sampled packet.
> ... Equivalent to the following actions of ovs-ofctl command:
> 	sample()

therefore:
- we can add this action to flows we wish to sample.
- we must use OpenFlow >= 1.3

## sample() Action in practice
We will demonstrate the use of the `sample()` action in a simple controller.
This controller is based on the simple L2 switch controller for OpenFlow1.4.
The full source code is available from `ryu/ryu/app/simple_switch14.py`.

Ryu controllers are event-driven. When a packet-in message is recieved from the
switch (meaning a flow-miss has occcured in the switch, and the switch must ask
the controller how to handle the packet) the `_packet_in_handler`
method will be invoked. This method implements an L2 switch by maintaining a
mapping of mac addresses to ports. If it finds the correct port, the method
will install a flow record that will forward subsequent packets.

This is where we make our modification:

```python
sample_action = [datapath.ofproto_parser.NXActionSample(probability=65535,
	collector_set_id=1,
	obs_domain_id=2,
	obs_point_id=3,)]
actions = sample_action + actions
self.add_flow(datapath, 1, match, actions)
```

In addition to the forwarding action, we add a `sample()` action to perform
sampling per flow. Here, the parameters are hard-coded for proof of concept.
Nevertheless it should be simple to adjust the parameters (for instance, have a
different sampling rate for different source mac address) or only install the
sampling action for specific flows.

The full source code for our modified controller is available as
`sampling_switch14.py`. It can be run by issuing the following command:
```
ryu-manager sampling_switch14.py
```
