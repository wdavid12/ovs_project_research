# What I have learned so far

## Background
In OVS, the switching component (which is implemented as a kernel module in our
case) is called the 'datapath'. The datapath maintaines a cache of actions that
need to be executed for each flow. When a packet does not hit the cache, the
datapath must consult with the userspace component (ovs-vswitchd) using dpif.

dpif (datapath interface) is a binary protocol over netlink that allows the
kernel module to send messages to userspace. When a message is sent from
kernel-space to userspace, this is called an 'upcall'. As stated earlier,
an upcall will occur when a recieved packet does not match any cached flow,
or when an action specifically requires it (as is the case for sampling).

## sFlow
The sFlow implementation in OVS is contained in a small library called
libsflow. relevant files:

- lib/sflow.h
- lib/sflow_agent.c
- lib/sflow_api.h
- lib/sflow_poller.c
- lib/sflow_reciever.c
- lib/sflow_sampler.c

Obviously the API is contained in sflow_api.h
The implementation expects samples to be handed to it using
`sfl_sampler_writeFlowSample` (found in `lib/sflow_api.h:310`).
Before sampling can begin, some internal data structures need to be
initialized, among them:

- SFLSampler
- SFLAgent
- SFLReciever

More research is required before I know how the library is meant to be used.

## OVS userspace
The userspace component of an OVS bridge can be found in the `ofproto/`
directory. This is a library (`libofproto`) which is in charge of implementing
OpenFlow in userspace, and among other duties must read messages from dpif and
handle them. When an upcall is recieved, it will be handed to the code in
`ofproto/ofproto-dpif-upcall.c`. Depending on the upcall type, we may need to
call functions from `ofproto/ofproto-dpif-xlate.c` to figure out what to do.
This is the case for an UPCALL_MISS (cache miss in kernel-mode).

Most of the code that deals with sFlow can be found in a single file:
`ofproto/ofproto-dpif-sflow.c`.

When sFlow is enabled, `set_sflow` from `ofproto/ofproto-dpif.c:2009` will be
called. This function proceeds to call `dpif_sflow_add_port` (from
`ofproto/ofproto-dpif-sflow.c:643`) on every port in the bridge.

`dpif_sflow_add_port` will insert each port to an internal hash table and
will create an sFlow poller for the port.

`set_sflow` will also set the polling probability (it is global, not per flow)
and will invalidate the state in the kernel module (line 2027.)
*TODO: How is the kernel mode cache actually invalidated?*

### Really activating sFlow
When a packet is first recieved, a miss upcall will happen (as described above)
and `xlate_actions` from `ofproto/ofproto-dpif-xlate.c:6826` will be called.
*TODO: How exactly do we reach this function?*

If sFlow is eanbled, `compose_sflow_action` (line 7082) will be called.
This is a wrapper around `compose_sample_action` (line 2917) where the real work happens.
For every flow (*TODO: This could be the key! We can call this function only
for specific flows!!!*) we are going to add an OVS_ACTION_ATTR_SAMPLE and
set the probability with OVS_SAMPLE_ATTR_PROBABILITY. Now inside a nested
action (*TODO: learn more about a nested actions*) we add an OVS_ACTION_USERSPACE
with `odp_put_userspace_action`.
- Note: All of this is done with functions like `nl_msg_put_u32` because we are
  building a binary netlink packet.


## OVS kernel-mode
Now that we have installed some sampling actions in the kernel, they will be
used in `datapath/actions.c`. OVS_ACTION_ATTR_SAMPLE is handled in line 1292 by
calling `sample`. This function (line 1044) will perform the actual sampling
(lines 1059-1060), and if it determines the current packet should be sampled it
will execute the nested actions on a copy of the packet.

The nested OVS_ACTION_USERSPACE is handled on line 1243 and will call
`output_userspace` which will generate an upcall.

## Back to userspace
As stated earlier, the upcall will be handled by
`ofproto/ofproto-dpif-upcall.c`.
`process_upcall` on line 1351 will handle the SFLOW_UPCALL on line 1364 by
finally calling `dpif_sflow_recieved`.
*TODO: after `dpif_sflow_recieved` is called, how do we find the right sflow
sampler? There is a seperate sampler per bridge!*

## Notes:
- I have ignored some details with the sampling action. I think some cookie
is passed to the kernel module along with every action, and that is how
userspace knows that it is an SFLOW_UPCALL when it gets it back.
- The sampling is already done by adding a special action to the flows.
if we only add it to _specific_ flows, we should get what we want, but it probably
won't be _that_ simple. We will also need to change ofproto-dpif-sflow.c or
some other file so we can add a seperate SFLSampler for each flow, and then
we need to find it somehow. Or perhaps we can use a global sampler?
