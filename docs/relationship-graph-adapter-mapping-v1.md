# Relationship Graph Adapter Mapping Matrix (v1)

This matrix defines how source adapters emit graph node/edge facts with evidence references.

| Source adapter | Observed fact | Node upserts | Edge upserts | Evidence ref pattern |
|---|---|---|---|---|
| Docker | container metadata (id, host, networks) | `container`, `host`, `network` | `host -> container (runs)`, `container -> network (attached_to_network)` | `fact:<fact_id>` |
| Docker | container exposed ports / service process hints | `service`, `port` | `container -> service (contains)`, `service -> port (listens_on)` | `fact:<fact_id>` |
| Proxmox | VM inventory + host mapping | `host`, `vm` | `host -> vm (hosts)` | `fact:<fact_id>` |
| Proxmox | VM disk/storage attachment | `storage` | `vm -> storage (mounts)` | `fact:<fact_id>` |
| Proxmox | PCI passthrough / GPU assignment | `gpu` | `vm -> gpu (uses_gpu)` | `fact:<fact_id>` |
| Log-derived service facts | dependency failure indicators | `service` (if missing) | `service -> service (depends_on)` | `log:<log_entry_id>` |

## Rules

1. Node identity uses (`entity_type`, `entity_ref`, `site_id`).
2. Edge identity uses (`from_node_id`, `to_node_id`, `edge_type`).
3. Upserts must be idempotent.
4. Missing edges become stale before cleanup.
5. Cross-site edges must include explicit evidence proving linkage.
