# BarriApp — Revenue Projection (Year 1)

> Status: **Illustrative model**. This is a planning estimate, **not a forecast**.
> It projects platform **revenue** (commissions + subscriptions), **not net
> profit** — operating costs (infra, salaries, marketing, support, payment ops)
> are **not** deducted here. All figures in **COP** unless noted; USD at
> **1 USD ≈ 4,000 COP**. Every input is adjustable — change the assumptions and
> the table recomputes. Based on [COMMISSION_AND_SUBSCRIPTION.md](COMMISSION_AND_SUBSCRIPTION.md).

## 1. Assumptions (adjustable)

| Input | Value | Rationale |
|-------|-------|-----------|
| Commission rate | **12%** | Midpoint of the ~8–15% launch range |
| Average order value (items) | **COP $25,000** | Small neighborhood-store ticket |
| Orders per active client / month | **4** | Roughly weekly purchase |
| Online payment share (Wompi) | **40%** | Rest is cash |
| Wompi fee (absorbed) | **≈1.45% of GMV** | 3.15% × online share × (items+delivery uplift) |
| Delivery fee | **100% to collaborator** | Not platform revenue |
| Subscription price (Premium) | **COP $29,900 / month** | Illustrative |
| Subscription availability | **From month 4** (post-MVP) | Months 1 & 3 show $0 subscription |

**Growth trajectory** (monthly active clients / active stores):

| Month | Active clients | Active stores | Premium adoption |
|------:|---------------:|--------------:|-----------------:|
| 1  |    400 |    25 | 0% (not launched) |
| 3  |  1,500 |    90 | 0% (not launched) |
| 5  |  4,000 |   220 | 10% |
| 9  | 12,000 |   600 | 18% |
| 12 | 25,000 | 1,200 | 25% |

> Growth reflects neighborhood-by-neighborhood expansion in a single city. These
> are **planning placeholders** — replace with real traction data as it comes in.

## 2. Formulas

```
GMV (items)        = active_clients × orders_per_client × AOV
Gross commission   = GMV × commission_rate
Wompi cost         ≈ GMV × 1.45%            (absorbed by platform)
Net commission     = Gross commission − Wompi cost
Subscription rev.  = active_stores × premium_adoption × subscription_price
Total net revenue  = Net commission + Subscription revenue
```

> Simplification: Premium stores pay a *reduced* commission (offset by the
> subscription fee). This model applies the flat 12% to all GMV and adds
> subscription on top; the two effects roughly cancel, so totals stay indicative.

## 3. Monthly revenue at each milestone

Figures are the revenue **generated in that month** (not cumulative).

| Month | Orders/mo | GMV (items) | Gross commission | Wompi cost | Subscription | **Total net revenue** | ≈ USD |
|------:|----------:|------------:|-----------------:|-----------:|-------------:|----------------------:|------:|
| 1  |   1,600 |   $40,000,000 |    $4,800,000 |    −$580,000 |         $0 |   **$4,220,000** |  ~$1,055 |
| 3  |   6,000 |  $150,000,000 |   $18,000,000 |  −$2,175,000 |         $0 |  **$15,825,000** |  ~$3,956 |
| 5  |  16,000 |  $400,000,000 |   $48,000,000 |  −$5,800,000 |   $657,800 |  **$42,857,800** | ~$10,714 |
| 9  |  48,000 |$1,200,000,000 |  $144,000,000 | −$17,400,000 | $3,229,200 | **$129,829,200** | ~$32,457 |
| 12 | 100,000 |$2,500,000,000 |  $300,000,000 | −$36,250,000 | $8,970,000 | **$272,720,000** | ~$68,180 |

**Subscription detail:** M5 = 22 premium stores, M9 = 108, M12 = 300, each × $29,900.

## 4. Approximate cumulative year-1 revenue

Interpolating monthly growth between the milestones, cumulative **net revenue for
the first 12 months** lands in the order of **~COP $1.0–1.2 billion**
(**~USD $250k–300k**), dominated by commissions; subscriptions add a small but
growing slice (single-digit % early, ~3% of monthly revenue by month 12). Exact
cumulative depends on the month-by-month curve — treat as an order of magnitude.

## 5. Sensitivity (what moves the needle most)

| Lever | Effect |
|-------|--------|
| **Active clients / retention** | Linear on the whole model — the #1 driver |
| **Orders per client** | Linear on GMV → linear on commission |
| **Commission rate** | Each +1pt ≈ +8.3% commission revenue (from 12%) |
| **AOV** | Linear on GMV |
| **Premium adoption / price** | Small early, grows; a second revenue leg over time |
| **Online share** | Higher online = more absorbed Wompi cost (lowers net) |

## 6. Important caveats
- **Revenue, not profit.** Subtract operating costs (cloud/Atlas/Redis/R2, Mapbox,
  FCM/SMS, salaries, marketing/CAC, support, Wompi already netted) to get to
  margin. Early months are almost certainly **operating at a loss** while acquiring
  users.
- **Two-sided cold start.** The growth curve assumes successful neighborhood
  seeding (enough stores + collaborators + clients simultaneously); real ramp may
  be slower.
- **Placeholders.** Every number here is an assumption to be replaced with real
  data. Keep this doc updated as the flywheel turns.
