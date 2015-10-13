[clusters]
atlas_c1 =
    10.17.0.105:8091
atlas_c2 =
    10.17.0.106:8091

[clients]
hosts =
    10.5.3.35
credentials = root:couchbase

[storage]
data = /opt/couchbase/var/lib/couchbase/data
index = /opt/couchbase/var/lib/couchbase/data

[credentials]
rest = Administrator:password
ssh = root:couchbase

[parameters]
Platform = Physical
OS = CentOS 6.5
CPU = Intel Xeon E5-2680 v2 (40 vCPU)
Memory = 256 GB
Disk = RAID 10 SSD