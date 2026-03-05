# I Built a Real-Time Financial Data Platform on GCP. Here Is What I Learned.

*Streaming transactions, daily settlements, and windowed fraud detection: three pipelines, one dataset, one reconciliation query.*

*All data in this project is fully synthetic. Transactions, merchants, amounts, settlement records, and fraud flags were generated programmatically for demonstration purposes. All figures are non-production and do not represent real financial activity.*

## Where This Started

I wanted to build something that felt real. Not a tutorial where everything works on the first try and the dataset is called sample_data.csv. I wanted to build something that reflected how financial data actually moves: messy, fast, and spread across multiple systems that do not always agree with each other.

So I set up a three-pipeline data platform on Google Cloud Platform using Dataflow, Pub/Sub, BigQuery, and Apache Beam. I hit failures, debugged them, and fixed them. At the end, 18 of 18 automated verification checks passed.

This article walks through what I built, why I made the decisions I made, and what I would do differently in production.

## The Problem I Was Solving

Every payment platform has the same fundamental data problem. When a card is swiped, you capture the transaction immediately. But the bank does not confirm the money actually moved until the next day, in a batch file called a settlements report.

Those two records, the real-time transaction and the settled record, come from different systems, arrive at different times, and need to be joined together to answer the most important question in financial data: what did we actually collect?

On top of that, you need fraud detection that works in real time. Not a daily batch job that tells you about fraud yesterday. Something that surfaces suspicious patterns as they are happening.

That is the problem I built for.

## The Three Builds

### Build 1: Streaming Pipeline

The first pipeline captures live transactions as they happen.

A Python script generates synthetic financial transactions and publishes them to Cloud Pub/Sub at one event per second. Each event represents a card transaction with a merchant name, amount, card type, currency, and a fraud flag. The publisher produced 3,111 synthetic transactions totaling $7.1 million in volume across the session.

A managed Dataflow template reads from the Pub/Sub subscription and writes each event to BigQuery within two minutes. The destination table is `transactions_raw` with 10 columns. A schema JSON file in Cloud Storage tells the template how to map the message fields to BigQuery columns.

I also configured a dead-letter table. Any message Dataflow cannot parse gets written to `transactions_raw_dlq` instead of being silently dropped. After 3,111 transactions, the dead-letter count was zero. Every message parsed cleanly.

**The failure I hit:** My first attempt used an e2-micro worker, which has 1 GB of RAM. Dataflow needs more than that to run the Beam SDK and the pipeline simultaneously. The job reached JOB_STATE_FAILED within two minutes. Switching to e2-medium (4 GB RAM) fixed it. The second attempt reached JOB_STATE_RUNNING and stayed there.

I kept that failed job in my documentation. It is a real debugging moment and it shows something a clean tutorial never does: resource sizing matters and you learn it by getting it wrong.

### Build 2: Batch Pipeline

The second pipeline loads the daily settlements file.

A Python script generates a CSV with 200 synthetic settlement records across three states: SETTLED (176 records), REVERSED (17 records), and HELD (7 records). Each SETTLED record includes a gross amount, a processing fee between 1.5 and 2.9 percent, and a net amount after fees. The file is uploaded to Cloud Storage and the Dataflow job reads it from there.

This time I used the GCS Text to BigQuery managed template, but with a JavaScript UDF, a User Defined Function that runs on each row before it is written to BigQuery. The UDF does three things: skips the CSV header row, skips malformed rows with fewer than 10 fields, and normalizes the settlement status to uppercase.

That last point matters. If the status field arrives as settled instead of SETTLED, every GROUP BY query breaks. The UDF handles it once at load time rather than in every downstream query.

After the job completed in 3 minutes and 16 seconds, I ran three data quality checks. The row count matched the generator output exactly. The total net amount matched to the cent: $396,306.72 in synthetic net revenue. Zero rows had null values in the required fields. The batch job was verified before anyone queried it.

I also set up a Cloud Scheduler job to trigger the batch pipeline automatically at 2 AM Eastern every night. I tested it with a Force Run and confirmed a new Dataflow job appeared in the console within 30 seconds.

### Build 3: Custom Apache Beam Pipeline

The third pipeline is where I stopped using managed templates and wrote actual code.

I built a custom Apache Beam Python pipeline that reads the same Pub/Sub topic as Build 1, groups transactions into 5-minute tumbling windows, and computes a fraud summary for each window. Any window where flagged transactions exceed 10 percent of total volume is written to BigQuery as HIGH_RISK.

The pipeline has seven stages:

1. Read from Pub/Sub
2. Parse JSON (custom DoFn)
3. Add event timestamps
4. Apply 5-minute fixed windows
5. Collect all transactions in the window into a list
6. Aggregate the list (custom DoFn)
7. Write to BigQuery

The two custom DoFn classes, ParseTransaction and AggregateWindow, contain all the business logic. ParseTransaction handles malformed messages gracefully by catching exceptions and dropping bad records instead of crashing the pipeline. AggregateWindow computes the total volume, flagged volume, fraud rate percentage, top merchant by transaction count, and top card type by volume.

Two windows were captured during the session. Both were HIGH_RISK.

| Metric | Window 1 | Window 2 |
|---|---|---|
| Time | 18:15 to 18:20 | 18:20 to 18:25 |
| Transactions | 238 (synthetic) | 201 (synthetic) |
| Flagged | 88 | 88 |
| Fraud Rate | 36.97% | 43.78% |
| Risk Level | HIGH_RISK | HIGH_RISK |
| Top Merchant | McDonalds | Uber |

The fraud rates are high because the synthetic publisher flags any transaction over $3,000, and the random amounts frequently exceed that threshold. In production you would calibrate the threshold to match historical baseline fraud rates, which are typically below 2 percent.

## The Reconciliation Query

The payoff for all three builds is a single SQL query that joins all three tables together.

```sql
SELECT
  fw.window_start,
  fw.window_end,
  fw.total_transactions        AS streamed_transactions,
  fw.flagged_transactions,
  fw.fraud_rate_pct,
  fw.risk_level,
  fw.top_merchant,
  COUNT(s.settlement_id)       AS settled_count,
  ROUND(SUM(s.net_amount), 2)  AS settled_net_revenue,
  ROUND(SUM(s.fee_amount), 2)  AS total_fees_paid,
  COUNTIF(s.settlement_status = 'REVERSED') AS reversals,
  COUNTIF(s.settlement_status = 'HELD')     AS held_count
FROM `[PROJECT-ID].transactions.fraud_windows` fw
LEFT JOIN `[PROJECT-ID].transactions.settlements_daily` s
  ON DATE(fw.window_start) = s.settlement_date
LEFT JOIN `[PROJECT-ID].transactions.transactions_raw` t
  ON t.timestamp BETWEEN fw.window_start AND fw.window_end
GROUP BY
  fw.window_start, fw.window_end,
  fw.total_transactions, fw.flagged_transactions,
  fw.fraud_rate_pct, fw.risk_level, fw.top_merchant
ORDER BY fw.window_start DESC
```

One query. Three tables. Three different pipelines feeding one result.

With synthetic data, the streaming and settlement tables do not share transaction IDs because each system generated its own random UUIDs independently. In production, both systems would receive the same transaction ID from the point-of-sale terminal at the moment the card is swiped. The join logic is correct. The synthetic data constraint is an expected limitation of this type of demonstration project.

## What This Architecture Is

If you have studied data engineering, you may recognize the lambda architecture pattern here.

The lambda architecture combines a fast layer and a slow layer to serve both low-latency and high-accuracy results.

Build 1 is the speed layer. Transactions appear in BigQuery within two minutes of happening. They are fast but not final: a transaction can still reverse.

Build 2 is the batch layer. The settlements file is the bank confirming what actually moved money. It arrives hours later but it is the source of truth.

The reconciliation query is the serving layer. It combines both to answer the question accurately.

Build 3 sits on top as a windowed analytics layer. It adds stateful aggregations over time that neither a streaming template nor a batch job can produce on their own.

## What I Would Add in Production

A dedicated service account with minimum required roles rather than the Compute Engine default service account. In production, using a default service account violates least-privilege principles and creates audit trail problems.

Schema validation before the streaming job writes to BigQuery. Right now, a publisher change that renames a field would silently route records to the dead-letter table with no alert. A schema registry and a pre-write validation step would catch that before data is lost.

Cloud Monitoring alerts on the dead-letter row count. Any non-zero value in that table should page someone immediately.

Eventarc triggers instead of Cloud Scheduler for the batch job. Cloud Scheduler fires at 2 AM regardless of whether the settlements file has arrived. Eventarc fires the moment the file lands in the GCS bucket. That is more robust when the bank delivers the file late.

Partitioned BigQuery tables. At scale, querying an unpartitioned transactions table over a full year is expensive. Partitioning by DATE(timestamp) makes single-day queries fast and cheap.

Terraform for all resources. The current setup uses gcloud commands. Terraform makes the infrastructure version-controlled, reviewable, and reproducible across environments.

## The Verification

At the end of the project I ran a verification script that executed 18 automated checks across all three builds. Every check passed.

The checks covered row counts, data quality (net amount math, null fields, uppercase normalization), fraud detection correctness (HIGH_RISK windows present, fraud rates above zero, window durations exactly 5 minutes), Dataflow job history, and the three-way join.

18 of 18. No data loss. No silent failures. No mismatches.

## What I Took Away From This

A few things stood out after building all three pipelines.

Managed templates are powerful but they have a ceiling. The moment I needed stateful processing across time, I had to write code. Understanding when to reach for a template and when to write a custom pipeline is a judgment call that only comes from building both.

Drain is not the same as cancel. Every streaming job in this project was stopped with a drain command, which flushes in-flight messages before shutting down. Using cancel on a financial pipeline can lose transactions. The distinction matters and it is not obvious until you look it up.

Data quality is a design decision, not an afterthought. The dead-letter table, the UDF header skip, the net amount verification: none of these are complicated. But they all have to be planned before the pipeline runs, not bolted on after data goes missing.

The reconciliation join is the architecture. Any engineer can build a streaming pipeline or a batch job in isolation. The interesting work is connecting them in a way that answers questions neither can answer alone.

## Resources

The full code, SQL queries, schema files, verification script, and architecture diagram are on GitHub.

The three builds covered in this article:

- Build 1: Managed Dataflow template, Pub/Sub to BigQuery streaming
- Build 2: Managed Dataflow template with JavaScript UDF, GCS batch load with Cloud Scheduler
- Build 3: Custom Apache Beam Python pipeline with 5-minute tumbling windows

*All data referenced in this article is synthetic and was generated programmatically. Figures including transaction counts, dollar amounts, fraud rates, and settlement totals are non-production values used for demonstration purposes only. All GCP project identifiers have been redacted.*
