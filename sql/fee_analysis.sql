-- Card network fee analysis
SELECT
  card_type,
  COUNT(*)                               AS settlements,
  ROUND(SUM(settled_amount), 2)          AS gross,
  ROUND(SUM(fee_amount), 2)              AS fees,
  ROUND(SUM(net_amount), 2)              AS net,
  ROUND(SUM(fee_amount) /
    NULLIF(SUM(settled_amount),0)*100, 3) AS effective_fee_rate
FROM [PROJECT-ID].transactions.settlements_daily
WHERE settlement_status = 'SETTLED'
GROUP BY card_type
ORDER BY effective_fee_rate DESC
