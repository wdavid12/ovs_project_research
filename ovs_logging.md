# OVS logging API

The OVS logging API can be found in `include/openvswitch/vlog.h`.

Every module (basically file) in OVS is expected to call the
`VLOG_DEFINE_THIS_MODULE(NAME)` macro with the module name.
This will create a local `struct vlog_module` which can be used to perform
per-module configuration (see later).

Logging is performed by calling:

```c
VLOG_FATAL(...)
VLOG_ERR(...)
VLOG_WARN(...)
```

and so on. The defualt log level is "warn", which means that calls to lower log
level functions such as `VLOG_DBG` and `VLOG_INFO` will be ignored.

OVS also has an API for rate-limiting log messages. Most modules already
utilize by creating a `struct vlog_rate_limit rl` which is initialized using
`VLOG_RATE_LIMIT_INIT(RATE,BURST)`. Using the API is simple, simple call

```c
VLOG_WARN_RL(&rl, ...)
```

instead of the usual `VLOG_WARN`. Up to `RATE` messages per minute will be
allowed, with a maximum burst of `BURST` messages.

# Printing packets
One particularly useful function is `ofp_print_dp_packet`. The API can
be found in `include/openvswitch/ofp-print.h`.
This function take a `struct dp_packet *` from the network, extracts
all the important metadata and prints it to a `FILE *` of your choice.
