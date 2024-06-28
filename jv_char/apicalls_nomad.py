import requests
    
def get_token(url, username, password):
    # Get a token from the api, login
    response = requests.get(
        f'{url}/auth/token', params=dict(username=username, password=password))
    return response.json()['access_token']

def get_batch_ids(url, token, batch_type="HySprint_Batch"):
    query = {
        'required': {
            'data': '*'
        },
        'owner': 'visible',
        'query': {'entry_type':batch_type},
        'pagination': {
            'page_size': 10000
        }
    }
    response = requests.post(
        f'{url}/entries/archive/query', headers={'Authorization': f'Bearer {token}'}, json=query)
    data = response.json()["data"]
    return [d["archive"]["data"]["lab_id"] for d in data if "lab_id" in d["archive"]["data"]]

def get_ids_in_batch(url, token,batch_ids, batch_type="HySprint_Batch"):
    query = {
        'required': {
            'data': '*'
        },
        'owner': 'visible',
        'query': {'results.eln.lab_ids:any': batch_ids, 'entry_type':batch_type},
        'pagination': {
            'page_size': 100
        }
    }
    response = requests.post(
        f'{url}/entries/archive/query', headers={'Authorization': f'Bearer {token}'}, json=query)
    data = response.json()["data"]
    sample_ids = []
    for d in data:
        dd = d["archive"]["data"]
        if "entities" in dd:
            sample_ids.extend([s["lab_id"] for s in dd["entities"]])
    return sample_ids
