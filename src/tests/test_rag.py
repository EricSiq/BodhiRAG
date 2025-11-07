# test_rag.py
import asyncio
import requests
import json

def test_rag_query():
    url = "http://localhost:8000/api/v1/chat"
    payload = {
        "query": "What countermeasures exist for microgravity-induced bone loss?",
        "use_kg": True,
        "use_vector": True,
        "mobile_optimized": True
    }
    
    try:
        response = requests.post(url, json=payload)
        print("Status Code:", response.status_code)
        print("Response:")
        print(json.dumps(response.json(), indent=2))
        
        # Check if we got real data
        data = response.json()
        if "mock" in data.get('answer', '').lower():
            print("❌ STILL GETTING MOCK DATA")
        else:
            print("✅ REAL RAG DATA RECEIVED")
            
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_rag_query()