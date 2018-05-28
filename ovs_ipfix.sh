#!/bin/bash

sudo ovs-vsctl -- --id=@br0 get Bridge br0 -- --id=@cs create \
    Flow_Sample_Collector_Set id=2 bridge=@br0 ipfix=@i -- --id=@i create IPFIX \
    targets=\"127.0.0.1:4739\" obs_domain_id=2 obs_point_id=3 \
    cache_active_timeout=5 cache_max_flows=13
