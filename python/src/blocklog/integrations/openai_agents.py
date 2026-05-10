def instrument_openai_agents(client):
    client.add_hook(lambda payload: payload)
    return client
