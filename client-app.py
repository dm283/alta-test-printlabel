# https://websockets.readthedocs.io/en/stable/howto/quickstart.html
#!/usr/bin/env python

import asyncio, websockets, json, time, datetime
import logging


# logger = logging.getLogger('websockets')
# logger.setLevel(logging.DEBUG)
# logger.addHandler(logging.StreamHandler())

TOKEN = 'adtb6ow34ickt4o396y25a'
URI = "wss://ts.a-m0.ru/ws/"
PROTOCOL_GUID = '8ab1aa20-03c3-11ef-8725-3b41761b2404' 
ORDER_GUID = '4a593110-fe1d-11ee-a6a3-3f6006cc05cc'
STATICTIC = True
REQUESTS_CNT = 3


async def workplace_action():
    print('set connection...')
    async with websockets.connect(uri=URI, subprotocols=['chat',]) as ws:
        print('ok. connected')

        # 1 Authentication
        json_auth = {
            "Operation": "Auth",
            "Data": {
                "Token": TOKEN,
            }
        }
        msg = json.dumps(json_auth)
        request = await ws.send(msg)
        print(msg)

        response = await ws.recv()
        print(response)

        # 2 Print Label
        start_time = datetime.datetime.now()

        for i in range(REQUESTS_CNT):
            code = "08051932421564"

            json_print = {
                "Operation": "PrintLabel",
                "Data": {
                    "Code": code,
                    "ProtocolGUID": PROTOCOL_GUID,
                    "OrderGUID": ORDER_GUID,
                    "Statistic": STATICTIC,
                }
            }
            msg = json.dumps(json_print)
            await ws.send(msg)
            print(msg)

            response = await ws.recv()
            if 'Data' in response:
                print('successfull response in received')
            else:
                print(response)

        finish_time = datetime.datetime.now()
        duration = (finish_time - start_time).total_seconds()
        print(duration, 'seconds')



if __name__ == "__main__":
    asyncio.run(workplace_action())
