# RetailCo GCP Dataflow Platform

A three-build financial data platform on Google Cloud Platform demonstrating streaming ingestion, batch loading, and custom windowed fraud detection using Apache Beam.

## Synthetic Data Disclaimer

All data in this project is fully synthetic. Transactions, merchants, amounts, settlement records, and fraud flags were generated programmatically for demonstration purposes. All figures are non-production and do not represent real financial activity.

## Architecture

Three pipelines feed a single BigQuery dataset and are joined in a reconciliation query.

- Build 1: Pub/Sub to BigQuery streaming via managed Dataflow template
- Build 2: GCS CSV to BigQuery batch load via managed Dataflow template with JavaScript UDF
- Build 3: Custom Apache Beam Python pipeline with 5-minute tumbling fraud windows

## Verification

18 of 18 automated checks passed across all three builds.

## Tech Stack

- Google Cloud Dataflow
- Google Cloud Pub/Sub
- Google BigQuery
- Google Cloud Storage
- Apache Beam Python SDK 3.12
- Cloud Scheduler
- Python 3

## Project Structure

    streaming/         Publisher script and Pub/Sub setup
    batch/             Settlements generator, schema JSON, JavaScript UDF
    beam/              Custom Apache Beam pipeline
    sql/               BigQuery analytics and reconciliation queries
    screenshots/       Console screenshots from each build
    docs/              Architecture diagram, Q&A explanation, Medium article

## Region and Worker Configuration

- Region: us-east1
- Worker type: e2-medium
- Max workers: 1
