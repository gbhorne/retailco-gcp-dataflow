function transformSettlement(line) {
  var fields = line.split(',');
  if (fields[0] === 'settlement_id') return null;
  if (fields.length < 10) return null;
  var result = {
    settlement_id:     fields[0].trim(),
    transaction_id:    fields[1].trim(),
    settled_amount:    parseFloat(fields[2]) || 0.0,
    fee_amount:        parseFloat(fields[3]) || 0.0,
    net_amount:        parseFloat(fields[4]) || 0.0,
    settlement_status: fields[5].trim().toUpperCase(),
    settlement_date:   fields[6].trim(),
    bank_reference:    fields[7].trim(),
    merchant_name:     fields[8].trim(),
    card_type:         fields[9].trim()
  };
  return JSON.stringify(result);
}
