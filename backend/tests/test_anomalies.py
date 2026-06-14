from datetime import datetime
from app.services.anomalies import anomaly_engine

def test_anomaly_mismatch_percentages():
    # Pizza Friday percentages sum to 110% (30 + 30 + 30 + 20)
    row_data = {
        "date": "28-02-2026",
        "description": "Pizza Friday",
        "paid_by": "Aisha",
        "amount": "14.40",
        "currency": "INR",
        "split_type": "percentage",
        "split_with": "Aisha;Rohan;Priya;Meera",
        "split_details": "Aisha 30%; Rohan 30%; Priya 30%; Meera 20%"
    }
    context = {"uploaded_rows": [row_data], "row_index": 0}
    anomalies = anomaly_engine.scan_record(row_data, context)
    
    types = [a.anomaly_type for a in anomalies]
    assert "PERCENTAGE_SUM_MISMATCH" in types

def test_anomaly_foreign_currency():
    row_data = {
        "date": "09-03-2026",
        "description": "Goa villa booking",
        "paid_by": "Dev",
        "amount": "540",
        "currency": "USD",
        "split_type": "equal",
        "split_with": "Aisha;Rohan;Priya;Dev"
    }
    context = {"uploaded_rows": [row_data], "row_index": 0}
    anomalies = anomaly_engine.scan_record(row_data, context)
    
    types = [a.anomaly_type for a in anomalies]
    assert "FOREIGN_CURRENCY" in types

def test_anomaly_date_ambiguity():
    # 04-05-2026 is ambiguous (Day 4, Month 5 vs Day 5, Month 4)
    row_data = {
        "date": "04-05-2026",
        "description": "Deep cleaning service",
        "paid_by": "Rohan",
        "amount": "25.00",
        "currency": "INR",
        "split_type": "equal",
        "split_with": "Aisha;Rohan;Priya"
    }
    context = {"uploaded_rows": [row_data], "row_index": 0}
    anomalies = anomaly_engine.scan_record(row_data, context)
    
    types = [a.anomaly_type for a in anomalies]
    assert "DATE_AMBIGUITY_WARNING" in types

def test_anomaly_settlement_record():
    # Rohan paid Aisha back (no split type or contains paid back)
    row_data = {
        "date": "25-02-2026",
        "description": "Rohan paid Aisha back",
        "paid_by": "Rohan",
        "amount": "50.00",
        "currency": "INR",
        "split_type": "",
        "split_with": "Aisha"
    }
    context = {"uploaded_rows": [row_data], "row_index": 0}
    anomalies = anomaly_engine.scan_record(row_data, context)
    
    types = [a.anomaly_type for a in anomalies]
    assert "SETTLEMENT_RECORD" in types
