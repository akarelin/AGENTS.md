---
description: Start all monitoring services (Netdata multi-node and LibreNMS)
---

Execute the monitoring control script to start all monitoring services:

```bash
cd /home/alex/RAN/Services && ./monitoring-control.sh start
```

This will:
- Start Netdata on seven (parent node)
- Start Netdata on five (child node)
- Start Netdata on trix (child node)
- Start LibreNMS

Access URLs will be displayed after startup.
