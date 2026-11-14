"""SYNTHETIC ONLY bank-like CSV fixture adapters (NOT certified real banks).

Never trust a bank format until an approved sanitized bank export is tested.
Converted CSV goes through the same conservative normalized reconciliation.
"""
from __future__ import annotations
import csv
from io import StringIO
from .importer import ImportErrorDetail, MAX_ROWS, parse_money

PROFILES={
    'normalized': 'date,description,debit,credit,balance,reference',
    'synthetic_split': 'Post Date,Narration,Withdrawals,Deposits,Running Balance,Transaction Ref',
    'synthetic_direction': 'Transaction Date,Details,Amount,Type,Closing Balance,Trace',
}

def normalize_synthetic_csv(content: bytes, profile: str, extension: str):
    """Return normalized CSV and explicit date format; no implicit guesses."""
    if profile == 'normalized':
        return content, None
    if profile not in PROFILES:
        raise ImportErrorDetail('Unknown or uncertified synthetic import profile')
    if extension != '.csv':
        raise ImportErrorDetail('Synthetic bank-like layouts currently require UTF-8 CSV')
    try:
        input_text = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ImportErrorDetail('CSV must be UTF-8') from None
    reader=csv.DictReader(StringIO(input_text,newline=''))
    required=[p.strip().lower() for p in PROFILES[profile].split(',')]
    provided=[str(p or '').strip().lower() for p in (reader.fieldnames or [])]
    if len(set(provided)) != len(provided) or provided != required:
        raise ImportErrorDetail('Synthetic bank-layout headers do not match selected profile')
    output=StringIO(newline='')
    writer=csv.writer(output)
    writer.writerow(['date','description','debit','credit','balance','reference'])
    count=0
    for row in reader:
        count+=1
        if count > MAX_ROWS or None in row:
            raise ImportErrorDetail('Malformed CSV or more than 5000 transactions')
        data={str(k).strip().lower(): str(v or '').strip() for k,v in row.items()}
        if profile=='synthetic_split':
            writer.writerow([data['post date'],data['narration'],data['withdrawals'],data['deposits'],data['running balance'],data['transaction ref']])
        else:
            amount=parse_money(data['amount'])
            direction=data['type'].upper()
            if direction not in {'DR','CR'} or amount is None or amount <= 0:
                raise ImportErrorDetail('Expected positive Amount with DR or CR direction')
            writer.writerow([data['transaction date'],data['details'], data['amount'] if direction=='DR' else '', data['amount'] if direction=='CR' else '',data['closing balance'],data['trace']])
    if count==0:
        raise ImportErrorDetail('No bank-layout rows found')
    return output.getvalue().encode('utf-8'),'%d/%m/%Y'
