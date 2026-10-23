def test_liveness_supports_head_and_get_without_authentication(client):
    assert client.get('/health/live').json()=={'status':'ok'}
    response=client.head('/health/live')
    assert response.status_code==200 and response.content==b''
