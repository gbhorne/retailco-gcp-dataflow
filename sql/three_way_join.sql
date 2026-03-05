-- Three-way reconciliation join across all three builds
SELECT
  fw.window_start,
  fw.window_end,
  fw.total_transactions                    AS streamed_transactions,
  fw.flagged_transactions,
  fw.fraud_rate_pct,
  fw.risk_level,
  fw.top_merchant,
  COUNT(s.settlement_id)                   AS settled_count,
  ROUND(SUM(s.net_amount), 2)              AS settled_net_revenue,
  ROUND(SUM(s.fee_amount), 2)              AS total_fees_paid,
  COUNTIF(s.settlement_status = 'REVERSED') AS reversals,
  COUNTIF(s.settlement_status = 'HELD')    AS held_count
FROM [PROJECT-ID].transactions.fraud_windows fw
LEFT JOIN [PROJECT-ID].transactions.settlements_daily s
  ON DATE(fw.window_start) = s.settlement_date
LEFT JOIN [PROJECT-ID].transactions.transactions_raw t
  ON t.timestamp BETWEEN fw.window_start AND fw.window_end
GROUP BY
  fw.window_start, fw.window_end,
  fw.total_transactions, fw.flagged_transactions,
  fw.fraud_rate_pct, fw.risk_level, fw.top_merchant
ORDER BY fw.window_start DESC
