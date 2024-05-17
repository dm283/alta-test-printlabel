import sys, asyncio, random, time, websockets, json, logging, os, configparser, statistics, socket
from colorama import just_fix_windows_console, Fore, Back, Style
from pathlib import Path

just_fix_windows_console()

config = configparser.ConfigParser()
config_file = os.path.join(Path(__file__).resolve().parent, 'config.ini')
if os.path.exists(config_file):
  config.read(config_file, encoding='utf-8')
else:
  print("error! config file doesn't exist"); sys.exit()

def get_codes():
    # gets list of code from outer source/file
    # code_list = ['4680648061203', ] # '4680648061200', ]
    with open('code-list.txt', 'r') as f:
        code_list = f.readlines()
        code_list = [c for c in map(lambda x: x.replace('\n', ''), code_list)]
    return code_list

def create_code_list(code_list, quantity):
    # creates list of defined quantity of codes
    created_list = list()
    for i in range(quantity):
        code = random.choice(code_list)
        created_list.append(code)
    return created_list

COLOR_SET = {
    1: Fore.YELLOW,
    2: Fore.CYAN,
    3: Fore.LIGHTGREEN_EX,
    4: Fore.LIGHTYELLOW_EX,
}

CHECK_AUTH = config.getboolean('default', 'check_auth')
PASS_IF_TASK_ERROR = config.getboolean('default', 'pass_if_task_error')
INSTANCES_COLORS_ENABLED = config.getboolean('default', 'instances_colors_enabled')
CNT_INSTANCES = int(config['default']['cnt_instances'])
if CNT_INSTANCES > len(COLOR_SET):
    INSTANCES_COLORS_ENABLED = False
CNT_INSTANCE_TASKS_PER_SEC = int(config['default']['cnt_instance_tasks_per_sec'])
CNT_CYCLES = int(config['default']['cnt_cycles'])
REQUEST_TIME_GAP = 1 / CNT_INSTANCE_TASKS_PER_SEC
# as there is a request-time-gap inside each cycle, cycle-gap is corrected by it
if int(config['default']['cycle_time_gap']) >= REQUEST_TIME_GAP:
    CYCLE_TIME_GAP = int(config['default']['cycle_time_gap']) - REQUEST_TIME_GAP
else:
    CYCLE_TIME_GAP = 0
# print(REQUEST_TIME_GAP, CYCLE_TIME_GAP)
# sys.exit()

TOKEN = config['default']['token']
URI = config['default']['uri']
PROTOCOL_GUID = config['default']['protocol_guid']
ORDER_GUID = config['default']['order_guid']
STATISTIC = config.getboolean('default', 'statistic')

CNT_INSTANCES_STARTED = int()
# CYCLE_START_TIME = {}
REQUEST_TIME_LIST = list()
RESPONSE_TIME_LIST = list()
RESPONSES_LIST = list()
CNT_ERRORS = int()
LATENCY_LIST = list()
DURATION_LIST = list()
PROCESS_TIME_LIST = list()
QUEUE_TIME_LIST = list()

CNT_TOTAL_REQUESTS = CNT_INSTANCES * CNT_INSTANCE_TASKS_PER_SEC * CNT_CYCLES
CODE_LIST = get_codes()
CODE_LIST = create_code_list(CODE_LIST, CNT_TOTAL_REQUESTS)


async def display_instance_text(instance_id, instance_color, text_to_display):
    # display text of particular instance
    # print(instance_color + f'instance [#{instance_id}]:  ' + text_to_display)
    pass


async def receive_response(ws, instance_id, instance_color, cnt_tsks):
    # receives all responses for instance
    global CNT_ERRORS

    for i in range(CNT_CYCLES * cnt_tsks):
        response = await ws.recv()
        response_time = time.monotonic()
        if 'Error' in response:
            CNT_ERRORS += 1; continue
        RESPONSE_TIME_LIST.append(response_time)
        RESPONSES_LIST.append(response)

        # uncomment it if display messages is needed!
        # text_msg = f'[ response ]:  {response_time}  --  {response}'
        text_msg = f'[ response ]:  {response_time}'
        await display_instance_text(instance_id, instance_color, text_msg)

    # old version
    # for cycle in range(CNT_CYCLES):
    #     for i in range(cnt_tsks):
    #         response = await ws.recv()
    #         if 'Error' in response:
    #             CNT_ERRORS += 1
    #             if PASS_IF_TASK_ERROR:
    #                 continue
    #         response_time = time.monotonic()
    #         RESPONSE_TIME_LIST.append(response_time)

    #         # text_msg = f'[ response ]:  {response_time}  --  {response}'
    #         text_msg = f'[ response ]:  {response_time}'
    #         await display_instance_text(instance_id, instance_color, text_msg)

    #         json_response = json.loads(response)
    #         PROCESS_TIME_LIST.append(json_response['Data']['ProcessTime'])
    #         QUEUE_TIME_LIST.append(json_response['Data']['QueueTime'])
        

async def create_request(ws, instance_id, instance_color, cnt_tsks):
    # creates all requests for instance
    json_msg = { "Operation": "PrintLabel", "Data": {
                "Code": '', "ProtocolGUID": PROTOCOL_GUID, "OrderGUID": ORDER_GUID, "Statistic": STATISTIC, } }
    
    for cycle in range(CNT_CYCLES):
        for task in range(cnt_tsks):
            json_msg['Data']['Code'] = CODE_LIST.pop()
            msg = json.dumps(json_msg)
            await ws.send(msg)
            request_time = time.monotonic()
            REQUEST_TIME_LIST.append(request_time)

            # uncomment it if display messages is needed!
            # text_msg = f'[ request ]:  {request_time}  --  {msg}'
            text_msg = f'[ request ]:  {request_time}'
            await display_instance_text(instance_id, instance_color, text_msg)

            await asyncio.sleep(REQUEST_TIME_GAP)
        
        await asyncio.sleep(CYCLE_TIME_GAP)
    
    
    # old version
    # for cycle in range(CNT_CYCLES):
    #     for i in range(cnt_tsks):
    #         code = CODE_LIST.pop()
    #         json_msg['Data']['Code'] = code
    #         msg = json.dumps(json_msg)
    #         await ws.send(msg)
    #         request_time = time.monotonic()
    #         REQUEST_TIME_LIST.append(request_time)
            
    #         # text_msg = f'[ request ]:  {request_time}  --  {msg}'
    #         text_msg = f'[ request ]:  {request_time}'
    #         await display_instance_text(instance_id, instance_color, text_msg)
    #         await asyncio.sleep(REQUEST_TIME_GAP)  #  
    #     # text_msg = f'turn {cycle+1} tasks created'#  {turn_time}'
    #     # await display_instance_text(instance_id, instance_color, text_msg)


async def instance_action_v1():
    # runs instance and its tasks
    global CNT_INSTANCES_STARTED
    CNT_INSTANCES_STARTED += 1
    instance_id = CNT_INSTANCES_STARTED
    instance_color = COLOR_SET[instance_id] if INSTANCES_COLORS_ENABLED else Fore.WHITE
    
    await display_instance_text(instance_id, instance_color, 'instance is created')
    await display_instance_text(instance_id, instance_color, 'set connection...')
    try:
        async with websockets.connect(uri=URI, subprotocols=['chat',]) as ws:
            await display_instance_text(instance_id, instance_color, 'ok. connected')

            # check latency of connection
            pong_waiter = await ws.ping()
            latency = await pong_waiter  # only if you want to wait for the corresponding pong
            LATENCY_LIST.append(latency)

            # # 1 Authentication
            json_auth = { "Operation": "Auth", "Data": { "Token": TOKEN, } }
            msg = json.dumps(json_auth)
            request = await ws.send(msg)
            await display_instance_text(instance_id, instance_color, msg)
            response = await ws.recv()
            await display_instance_text(instance_id, instance_color, response)
            if CHECK_AUTH and ('Пользователь не авторизован' in response):
                print('ERROR:  the user is not authorised!')
                sys.exit()

            # 2 Printlabel requests and responses
            await asyncio.gather(
                asyncio.create_task( create_request(ws, instance_id, instance_color, CNT_INSTANCE_TASKS_PER_SEC) ),
                asyncio.create_task( receive_response(ws, instance_id, instance_color, CNT_INSTANCE_TASKS_PER_SEC) ),
            )
    except Exception as ex:
        print('testing error: ', ex)
        sys.exit()
    

async def display_stats(report_color, indicator_list):
    # create and displays statistics in a report
    print(report_color + '[ min       ] =', min(indicator_list))
    print(report_color + '[ max       ] =', max(indicator_list))        
    print(report_color + '[ mean      ] =', round(statistics.mean(indicator_list)))
    print(report_color + '[ median    ] =', round(statistics.median(indicator_list)))
    print(report_color + '[ mode      ] =', round(statistics.mode(indicator_list)))
    print(report_color + '[ multimode ] =', statistics.multimode(indicator_list))


async def display_report(test_duration):
    # creates and displays a report
    report_color = Fore.LIGHTCYAN_EX
    error_color = Fore.LIGHTRED_EX if CNT_ERRORS else report_color
    list_title_color = Fore.LIGHTBLACK_EX
    list_values_color = Fore.WHITE
    DURATION_LIST = [round((RESPONSE_TIME_LIST[i]-REQUEST_TIME_LIST[i])*1000) for i in range(len(REQUEST_TIME_LIST))]
    request_response_total_test_time = round((RESPONSE_TIME_LIST[-1] - REQUEST_TIME_LIST[0])*1000)

    for response in RESPONSES_LIST:
        json_response = json.loads(response)
        PROCESS_TIME_LIST.append(json_response['Data']['ProcessTime'])
        QUEUE_TIME_LIST.append(json_response['Data']['QueueTime'])

    print(Style.RESET_ALL)
    print(Fore.LIGHTGREEN_EX + '*****************         PROGRESS REPORT        *****************')
    print(Fore.LIGHTYELLOW_EX +  '*  All time indicators - in milliseconds (ms)'); print()
    print(report_color + '[ latency/ping time            ] =', round(statistics.mean(LATENCY_LIST)*1000))
    print(report_color + '[ total test time              ] =', test_duration)
    print(report_color + '[ requests-responses test time ] =', request_response_total_test_time)
    print(report_color + '[ workplaces                   ] =', CNT_INSTANCES)
    print(report_color + '[ number of requests           ] =', CNT_INSTANCE_TASKS_PER_SEC, '(one workplace per second)')
    print(report_color + '[ number of requests           ] =', CNT_TOTAL_REQUESTS, '(total)') 
    print(error_color + '[ error responses              ] =', CNT_ERRORS)

    print(); print(Fore.LIGHTGREEN_EX + 'Response time (including send/receive, process, queue time):')
    await display_stats(report_color, DURATION_LIST)
    print(); print(Fore.LIGHTGREEN_EX + 'Process time:')
    await display_stats(report_color, PROCESS_TIME_LIST)
    print(); print(Fore.LIGHTGREEN_EX + 'Queue time:')
    await display_stats(report_color, QUEUE_TIME_LIST)
    
    print(); print(Fore.LIGHTGREEN_EX + 'Lists of values:')
    print(list_title_color + '[ response time values ] =' + list_values_color, DURATION_LIST)
    print(list_title_color + '[ response sorted values ] =' + list_values_color, sorted(DURATION_LIST))
    print(list_title_color + '[ process time values ] =' + list_values_color, PROCESS_TIME_LIST)
    print(list_title_color + '[ process time sorted values ] =' + list_values_color, sorted(PROCESS_TIME_LIST))
    print(list_title_color + '[ queue time values ] =' + list_values_color, QUEUE_TIME_LIST)
    print(list_title_color + '[ queue time sorted values ] =' + list_values_color, sorted(QUEUE_TIME_LIST))
    print(list_title_color + '[ requests list  ] =' + list_values_color, REQUEST_TIME_LIST)
    print(list_title_color + '[ responses list ] =' + list_values_color, RESPONSE_TIME_LIST)

    print(Style.RESET_ALL)


async def main():
    # the main entry function - runs setted number of instances and its tasks
    print(Fore.LIGHTMAGENTA_EX + f'Test has started. A total of {CNT_TOTAL_REQUESTS} requests will be made. Please wait.')
    start_test_time = time.monotonic()
    await asyncio.gather( *( instance_action_v1() for i in range(CNT_INSTANCES) ) )
    finish_test_time = time.monotonic()
    test_duration = round((finish_test_time - start_test_time)*1000)
    await display_report(test_duration)



if __name__ == '__main__':
    asyncio.run(main())
