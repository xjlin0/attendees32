async def websocket_application(scope, receive, send):
    """  WARNING: no session check here, only for local env!
    Testing (https://cookiecutter-django.readthedocs.io/en/latest/websocket.html)
    ws = new WebSocket('ws://0.0.0.0:8008');
    ws.onopen = function(e) { console.log('Connection established'); ws.send("Let's send a message to the server"); };
    ws.onmessage = function (e) { console.log(e.data) };
    ws.send('ping');    // pong!
    // for production Apache Reverse proxy setting see
      https://stackoverflow.com/a/18434449
      https://stackoverflow.com/a/28393526
    """
    while True:
        event = await receive()

        if event["type"] == "websocket.connect":
            await send({"type": "websocket.accept"})

        if event["type"] == "websocket.disconnect":
            break

        if event["type"] == "websocket.receive":
            if event["text"] == "ping":
                await send({"type": "websocket.send", "text": "pong!"})
