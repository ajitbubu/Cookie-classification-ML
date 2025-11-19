import requests
resp = requests.post(
    "http://localhost:9010/api/quick-scan",
    json={
        "domain_config_id": "9162f59e-ce11-46b7-93be-49e771496db2",
        "domain": "https://ir.exlservice.com",
        "customPages": [    
            #"/#main-content",
        ],
        "maxRetries": 3
    }
)
print(resp.json())