import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
from apache_beam.transforms.window import FixedWindows
import json
from datetime import datetime, timezone

PROJECT_ID       = "[PROJECT-ID]"
DATASET          = "transactions"
BUCKET           = "[PROJECT-BUCKET]"
REGION           = "us-east1"
INPUT_TOPIC      = f"projects/{PROJECT_ID}/topics/transactions-stream"
OUTPUT_TABLE     = f"{PROJECT_ID}:{DATASET}.fraud_windows"
TEMP_LOCATION    = f"gs://{BUCKET}/df-temp"
STAGING_LOCATION = f"gs://{BUCKET}/df-staging"

class ParseTransaction(beam.DoFn):
    def process(self, element):
        try:
            tx = json.loads(element.decode("utf-8"))
            yield tx
        except Exception:
            pass

class AggregateWindow(beam.DoFn):
    def process(self, element, window=beam.DoFn.WindowParam):
        transactions = list(element)
        if not transactions:
            return
        total    = len(transactions)
        flagged  = [t for t in transactions if t.get("is_flagged")]
        volume   = sum(t.get("amount", 0) for t in transactions)
        flag_vol = sum(t.get("amount", 0) for t in flagged)
        fraud_pct = round((len(flagged) / total) * 100, 2) if total > 0 else 0.0
        merchants = {}
        for t in transactions:
            m = t.get("merchant_name", "Unknown")
            merchants[m] = merchants.get(m, 0) + 1
        top_merchant = max(merchants, key=merchants.get) if merchants else "Unknown"
        cards = {}
        for t in transactions:
            c = t.get("card_type", "Unknown")
            cards[c] = cards.get(c, 0.0) + t.get("amount", 0)
        top_card = max(cards, key=cards.get) if cards else "Unknown"
        risk = "HIGH_RISK" if fraud_pct >= 10.0 else "NORMAL"
        yield {
            "window_start":         window.start.to_utc_datetime().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "window_end":           window.end.to_utc_datetime().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "total_transactions":   total,
            "total_volume":         round(volume, 2),
            "flagged_transactions": len(flagged),
            "flagged_volume":       round(flag_vol, 2),
            "fraud_rate_pct":       fraud_pct,
            "risk_level":           risk,
            "top_merchant":         top_merchant,
            "top_card_type":        top_card,
        }

def run():
    options = PipelineOptions([
        f"--project={PROJECT_ID}",
        f"--region={REGION}",
        f"--temp_location={TEMP_LOCATION}",
        f"--staging_location={STAGING_LOCATION}",
        "--runner=DataflowRunner",
        "--job_name=fraud-windows-beam",
        "--max_num_workers=1",
        "--worker_machine_type=e2-medium",
        "--save_main_session",
    ])
    options.view_as(StandardOptions).streaming = True
    with beam.Pipeline(options=options) as p:
        (
            p
            | "Read from PubSub"  >> beam.io.ReadFromPubSub(topic=INPUT_TOPIC)
            | "Parse JSON"        >> beam.ParDo(ParseTransaction())
            | "Add Timestamps"    >> beam.Map(
                lambda tx: beam.window.TimestampedValue(
                    tx,
                    datetime.fromisoformat(
                        tx["timestamp"].replace(" UTC","").replace(" ","T")
                    ).replace(tzinfo=timezone.utc).timestamp()
                )
            )
            | "5-Min Windows"     >> beam.WindowInto(FixedWindows(5 * 60))
            | "Group All"         >> beam.transforms.core.CombineGlobally(
                beam.transforms.combiners.ToListCombineFn()
            ).without_defaults()
            | "Aggregate Window"  >> beam.ParDo(AggregateWindow())
            | "Write to BigQuery" >> beam.io.WriteToBigQuery(
                OUTPUT_TABLE,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
            )
        )

if __name__ == "__main__":
    print("Launching fraud windows pipeline on Dataflow...")
    run()
    print("Pipeline submitted.")
