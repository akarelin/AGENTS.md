---
description: Stop all monitoring services (Netdata multi-node and LibreNMS)
---

Execute the monitoring control script to stop all monitoring services:

```bash
cd /home/alex/RAN/Services && ./monitoring-control.sh stop
```

This will:
- Stop Netdata on seven (parent node)
- Stop Netdata on five (child node)
- Stop Netdata on trix (child node)
- Stop LibreNMS
