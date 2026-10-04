# Cloudflare broker option vs existing SSH

Compared 2026-10-04 against primary Cloudflare docs. No Cloudflare
deployment was created. No purchase, token mint, or account change.

## Options in the docs

| Option | What it is | Spend / credentials | Fit |
| --- | --- | --- | --- |
| [Workers](https://developers.cloudflare.com/workers/platform/pricing/) | HTTP/RPC at the edge | Free: 100k req/day. Paid: **$5/month minimum** + usage | Needs a deployed Worker and account credentials |
| [Durable Objects](https://developers.cloudflare.com/durable-objects/) | Single-threaded coordination object | Paid plan $5/month; duration billed while active | Strong ordering, but a new shared cloud process |
| [Queues](https://developers.cloudflare.com/queues/reference/how-queues-works/) | At-least-once queue, Worker producer/consumer | Free: 10k ops/day. Paid: 1M ops/month then $0.40/million | Rival broker relative to native aplexer mailboxes |
| [Pub/Sub](https://developers.cloudflare.com/pub-sub/learning/integrate-workers/) | MQTT broker; Worker on-publish hook | Separate product; Worker publish/subscribe still beta-limited | Explicit rival production broker |

Queues are [now on the Workers Free plan](https://developers.cloudflare.com/changelog/product/queues/)
(10k operations/day). Durable Objects on Free are SQLite-backed only.
Workers Paid remains a **$5 USD/month** subscription. That is new spending.

## Constraints that rule out a fabricated deployment

- User authorization: no purchases, no new broad credentials, no secret copy.
- Aplexer rule: do not replace current messaging with a rival production broker.
- Native catalogs live on disk beside sessions. A Cloudflare Worker would
  need those catalogs exported, which copies private session metadata.
- Existing authenticated SSH already reaches Hetzner from Windows (`ssh.exe`,
  alias `hetzner`). It spends nothing extra.

## Choice

MVP uses the existing SSH alias allowlist and the installed aplexer CLI.
Cloudflare remains a documented alternative if spending and a Worker
deployment are later authorized. This file is not a claim that a
Cloudflare broker exists in this account.
