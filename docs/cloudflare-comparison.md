# Cloudflare Broker Option vs Existing SSH

Comparison performed 2026-10-04 against primary Cloudflare developer documentation.
**Verification guarantee**: No Cloudflare deployment was created. No purchase, token mint, credit card authorization, or account configuration change was performed.

## Options in Cloudflare Documentation

| Product | Architecture | Spend & Credentials | Fit / Assessment |
| --- | --- | --- | --- |
| [Workers](https://developers.cloudflare.com/workers/platform/pricing/) | HTTP/RPC edge execution | Free: 100k req/day (10ms CPU limit).<br>Paid: **$5.00 USD/month minimum** subscription + usage. | Requires account API tokens and external edge process; exposes session metadata outside local boundary. |
| [Durable Objects](https://developers.cloudflare.com/durable-objects/) | Strongly consistent, single-threaded in-memory coordination object with persistent storage | Requires Workers Paid (**$5/month minimum**). Active execution billed at $12.50 / million GB-seconds + $0.15 / million requests. | Strong global consistency and ordering, but introduces a new shared cloud process and recurring subscription spend. |
| [Queues](https://developers.cloudflare.com/queues/reference/how-queues-works/) | At-least-once distributed message queue with Worker consumers/producers | Free plan: 10,000 ops/day.<br>Paid plan: 1,000,000 ops/month then $0.40 / million. | Rival broker relative to native `aplexer` disk mailboxes; does not natively integrate with local host session states. |
| [Pub/Sub](https://developers.cloudflare.com/pub-sub/learning/integrate-workers/) | Managed MQTT broker with Workers integration | Independent product pricing; publish/subscribe integration remains beta-limited. | Explicit rival production broker; unnecessary protocol overhead for peer agent coordination. |

Primary docs citation:
- [Cloudflare Workers Pricing](https://developers.cloudflare.com/workers/platform/pricing/): Workers Paid is explicitly a **$5 USD/month** base fee.
- [Cloudflare Queues Availability](https://developers.cloudflare.com/changelog/product/queues/): Queues are available on Workers Free (10k ops/day), but cross-service coordination requires deployment tokens.

## Why Existing SSH is the Zero-Purchase Path

1. **Zero Financial Spend**:
   - Workers Paid is a minimum **$5/month** recurring subscription.
   - Existing SSH uses current infrastructure (Hetzner server + user workstation) with $0 incremental cost.

2. **Zero Credential Proliferation / No Secret Leakage**:
   - A Cloudflare deployment requires account credentials, API tokens, and Worker deploy keys stored on both machines.
   - Existing SSH uses existing keypairs already present in `~/.ssh/config` (`ssh.exe` alias `hetzner`) with strict `BatchMode=yes` and `StrictHostKeyChecking=yes`. No private keys are copied into repositories or passed across untrusted boundaries.

3. **No Rival Production Broker**:
   - Project rules strictly forbid replacing native `aplexer` messaging with a rival external broker.
   - Native `aplexer` catalogs and mailboxes reside on local disk (`.local/state/aplexer`) alongside the kernel cgroups and PTYs.
   - A Cloudflare broker would require synchronizing private session states, PID lists, and terminal histories to a public cloud, violating isolation boundaries.

4. **Direct Point-to-Point Reliability**:
   - Authenticated SSH provides end-to-end cryptographic integrity without depending on third-party edge reachability, DNS propagation, or cloud provider availability.

## Conclusion and Current Architecture

MVP strictly adopts **existing authenticated SSH** over the allowlisted device registry (`examples/devices.example.json`).
Human budget 2026-10-04: USD **$5/month TOTAL** including the existing Workers Paid **$5 base**. Remaining known headroom is **$0**. Account usage is unknown, so optional cloud activation is **fail-closed**. Default useful execution stays on Hetzner and user computers. No Workers agents, Containers, Workers AI, new paid services, billing changes, or service kills. No Cloudflare infrastructure or deployment exists in this account.
