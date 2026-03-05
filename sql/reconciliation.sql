-- Streaming vs batch reconciliation
SELECT
  'MATCHED' AS reconciliation_status,
  s.settlement_status,
  COUNT(*) AS count,
  ROUND(SUM(s.net_amount), 2) AS net_amount
FROM [PROJECT-ID].transactions.settlements_daily s
INNER JOIN [PROJECT-ID].transactions.transactions_raw t
  ON s.transaction_id = t.transaction_id
GROUP BY s.settlement_status

UNION ALL

SELECT
  'SETTLEMENT_ONLY' AS reconciliation_status,
  s.settlement_status,
  COUNT(*) AS count,
  ROUND(SUM(s.net_amount), 2) AS net_amount
FROM [PROJECT-ID].transactions.settlements_daily s
LEFT JOIN [PROJECT-ID].transactions.transactions_raw t
  ON s.transaction_id = t.transaction_id
WHERE t.transaction_id IS NULL
GROUP BY s.settlement_status

ORDER BY reconciliation_status, settlement_status
