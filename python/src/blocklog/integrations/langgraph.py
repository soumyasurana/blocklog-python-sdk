def instrument_langgraph(client):
    client.add_hook(lambda payload: payload)
    return client
