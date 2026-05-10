def instrument_langchain(client):
    client.add_hook(lambda payload: payload)
    return client
