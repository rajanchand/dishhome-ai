"""Vercel serverless entry-point.
Extremely simple to rule out import errors.
"""

async def app(scope, receive, send):
    if scope['type'] == 'lifespan':
        while True:
            msg = await receive()
            if msg['type'] == 'lifespan.startup':
                await send({'type': 'lifespan.startup.complete'})
            elif msg['type'] == 'lifespan.shutdown':
                await send({'type': 'lifespan.shutdown.complete'})
                return
    
    if scope['type'] != 'http':
        return

    # Basic Hello World response
    import json
    body = json.dumps({
        "status": "online",
        "message": "DishHome AI API is reachable",
        "path": scope.get("path")
    }).encode()
    
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            (b'content-type', b'application/json'),
            (b'access-control-allow-origin', b'*'),
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': body,
    })
