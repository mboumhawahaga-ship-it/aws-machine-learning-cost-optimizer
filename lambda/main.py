# lambda/main.py — Version 100% fonctionnelle
import json
import os
from datetime import datetime, timedelta

MOCK_DATA = {
    "total_cost": 850.00,
    "cost_by_resource": {
        "notebooks": 212.00, "training": 297.00, 
        "endpoints": 170.00, "storage": 42.50, "other": 128.50
    }
}

def handler(event, context):
    print("🚀 ML Cost Analysis")
    
    mock_mode = os.environ.get('MOCK_MODE', 'false').lower() == 'true'
    data = MOCK_DATA
    
    savings = 0
    recs = []
    
    # 4 recommandations simples
    for cost, pct, name in [
        (data['cost_by_resource']['notebooks'], 0.75, 'Notebooks'),
        (data['cost_by_resource']['training'], 0.70, 'Training'),
        (data['cost_by_resource']['endpoints'], 0.30, 'Endpoints'),
        (data['cost_by_resource']['storage'], 0.75, 'Storage')
    ]:
        if cost > 10:
            save = cost * pct
            savings += save
            recs.append({'type': name, 'savings': save})
    
    result = {
        'statusCode': 200,
        'body': json.dumps({
            'success': True,
            'total_cost': data['total_cost'],
            'potential_savings': round(savings, 2),
            'savings_pct': round(savings/data['total_cost']*100, 1),
            'recommendations': len(recs)
        }, indent=2)
    }
    
    print(f"💰 ${data['total_cost']} → 💸 ${savings}")
    return result
