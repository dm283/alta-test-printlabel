# https://websockets.readthedocs.io/en/stable/howto/quickstart.html
#!/usr/bin/env python

import asyncio, websockets, json, time, datetime
import logging


# logger = logging.getLogger('websockets')
# logger.setLevel(logging.DEBUG)
# logger.addHandler(logging.StreamHandler())

TOKEN = '7enk1p9sqce8msq2atcuyt'
URI = "wss://ts.a-m0.ru/ws/"
PROTOCOL_GUID = '2bfc39a0-080a-11ef-a7a0-bb86ff8a3b53'
ORDER_GUID = '2c68e830-0467-11ef-9d32-47ff33ac6ce5'
# PROTOCOL_GUID = '8ab1aa20-03c3-11ef-8725-3b41761b2404' 
# ORDER_GUID = '4a593110-fe1d-11ee-a6a3-3f6006cc05cc'
STATICTIC = True
REQUESTS_CNT = 1


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
            #code = "08051932421564"
            code = '4680648025847'

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
