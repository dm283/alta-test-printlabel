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
    with open('code-list.txt', 'r') as f:
        code_list = f.readlines()
        code_list = [c for c in map(lambda x: x.replace('\n', ''), code_list)]
    
    # code_list = ['4680648025847', '4680648061200', ] # '4680648061200', ]  4680648025847
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
ERRORS_LIST = list()
CNT_ERRORS = int()
LATENCY_LIST = list()
DURATION_LIST = list()
PROCESS_TIME_LIST = list()
QUEUE_TIME_LIST = list()
INSTANCE_TASKS_OVER_TIME = list()
CODES_OVER = dict()
INSTANCE_CODE_LISTS = dict()
INSTANCE_CURRENT_CODE = dict()
#CURRENT_CODE = CODE_LIST.pop()
EXCEPTIONS_LIST = list()

CNT_TOTAL_REQUESTS = CNT_INSTANCES * CNT_INSTANCE_TASKS_PER_SEC * CNT_CYCLES
CODE_LIST = get_codes()
# CODE_LIST = create_code_list(CODE_LIST, CNT_TOTAL_REQUESTS)


async def display_instance_text(instance_id, instance_color, text_to_display):
    # display text of particular instance
    print(instance_color + f'instance [#{instance_id}]:  ' + text_to_display)
    # pass


async def receive_response(ws, instance_id, instance_color, cnt_tsks):
    # receives all responses for instance
    # any response (successful and error) is appended to RESPONSES_LIST
    # as error response: (-1) is appended to RESPONSE_TIME_LIST instead response-time
    global CNT_ERRORS, INSTANCE_CURRENT_CODE, CODES_OVER

    for i in range(CNT_CYCLES * cnt_tsks):
        response = await ws.recv()
        response_time = time.monotonic()
        RESPONSES_LIST.append(response)

        # uncomment it if display messages is needed!
        # text_msg = f'[ response ]:  {response_time}  --  {response}'
        # text_msg = f'[ response ]:  {response_time}'
        # await display_instance_text(instance_id, instance_color, text_msg)

        if 'Error' in response:
            # text_msg = f'[ response ]:  {response_time}  --  error'
            text_msg = f'[ response ]:  {response_time}  --  error  --  {response}'
            await display_instance_text(instance_id, instance_color, text_msg)
            ERRORS_LIST.append( (response_time, response) )
            CNT_ERRORS += 1
            RESPONSE_TIME_LIST.append(-1)
            if len(INSTANCE_CODE_LISTS[instance_id]) > 0:
                INSTANCE_CURRENT_CODE[instance_id] = INSTANCE_CODE_LISTS[instance_id].pop()
            else:
                CODES_OVER[instance_id] = True
                return 0
        else:
            text_msg = f'[ response ]:  {response_time}  --  ok'
            await display_instance_text(instance_id, instance_color, text_msg)
            RESPONSE_TIME_LIST.append(response_time)


async def create_request(ws, instance_id, instance_color, cnt_tsks):
    # creates all requests for instance
    json_msg = { "Operation": "PrintLabel", "Data": {
                "Code": '', "ProtocolGUID": PROTOCOL_GUID, "OrderGUID": ORDER_GUID, "Statistic": STATISTIC, } }
    
    for cycle in range(CNT_CYCLES):
        for task in range(cnt_tsks):
            # json_msg['Data']['Code'] = CODE_LIST.pop()  # option #1
            json_msg['Data']['Code'] = INSTANCE_CURRENT_CODE[instance_id]       # option #2
            msg = json.dumps(json_msg)
            await ws.send(msg)
            request_time = time.monotonic()
            REQUEST_TIME_LIST.append(request_time)

            # uncomment it if display messages is needed!
            #text_msg = f'[ request ]:  {request_time}  --  {msg}'
            # text_msg = f'[ request ]:  {request_time}'
            text_msg = f'[ request ]:  {request_time}  --  {INSTANCE_CURRENT_CODE[instance_id]}'
            await display_instance_text(instance_id, instance_color, text_msg)

            await asyncio.sleep(REQUEST_TIME_GAP)

            if CODES_OVER[instance_id]:
                return 0
        
        await asyncio.sleep(CYCLE_TIME_GAP)


async def instance_action_v1():
    # runs instance and its tasks
    global CNT_INSTANCES_STARTED, CODES_OVER, INSTANCE_CODE_LISTS, INSTANCE_CURRENT_CODE, EXCEPTIONS_LIST
    CNT_INSTANCES_STARTED += 1
    instance_id = CNT_INSTANCES_STARTED
    instance_color = COLOR_SET[instance_id] if INSTANCES_COLORS_ENABLED else Fore.WHITE
    CODES_OVER[instance_id] = False
    INSTANCE_CODE_LISTS[instance_id] = CODE_LIST.copy()
    INSTANCE_CURRENT_CODE[instance_id] = INSTANCE_CODE_LISTS[instance_id].pop()
    
    # instances are created after a certain period of time
    instances_creation_time_gap = random.randint(0, 2000) / 1000
    await asyncio.sleep(instances_creation_time_gap)

    await display_instance_text(
        instance_id, instance_color, f'instance is created -- {time.monotonic()} -- {instances_creation_time_gap}')
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
            INSTANCE_TASKS_OVER_TIME.append(time.monotonic())
    except Exception as ex:
        print('testing error: ', ex)
        INSTANCE_TASKS_OVER_TIME.append(time.monotonic())
        EXCEPTIONS_LIST.append(ex)
        return instance_id, ex
        # sys.exit()
    

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
    responses_cnt_color = Fore.LIGHTRED_EX if len(RESPONSE_TIME_LIST) < len(REQUEST_TIME_LIST) else report_color
    list_title_color = Fore.LIGHTBLACK_EX
    list_values_color = Fore.WHITE

    # print('REQUEST_TIME_LIST =', REQUEST_TIME_LIST)
    # print('RESPONSE_TIME_LIST =', RESPONSE_TIME_LIST)

    if RESPONSE_TIME_LIST:
        for i in range(len(REQUEST_TIME_LIST)):
            if i < len(RESPONSE_TIME_LIST) and RESPONSE_TIME_LIST[i] != -1:
                duration = round((RESPONSE_TIME_LIST[i]-REQUEST_TIME_LIST[i])*1000)
                DURATION_LIST.append(duration)        
        operation_time_over = max(INSTANCE_TASKS_OVER_TIME)
        request_response_total_test_time = round((operation_time_over - REQUEST_TIME_LIST[0])*1000)

    for response in RESPONSES_LIST:
        if 'Error' not in response:
            json_response = json.loads(response)
            PROCESS_TIME_LIST.append(json_response['Data']['ProcessTime'])
            QUEUE_TIME_LIST.append(json_response['Data']['QueueTime'])

    print(Style.RESET_ALL)
    print(Fore.LIGHTGREEN_EX + '*****************         PROGRESS REPORT        *****************')
    print(Fore.LIGHTYELLOW_EX +  '*  All time indicators - in milliseconds (ms)'); print()

    if EXCEPTIONS_LIST:
        print(Fore.LIGHTRED_EX + f'{len(EXCEPTIONS_LIST)} workplaces stoped the work due to exception!\n')

    print(report_color + '[ latency/ping time            ] =', round(statistics.mean(LATENCY_LIST)*1000))
    print(report_color + '[ total test time              ] =', test_duration)
    if RESPONSE_TIME_LIST:
        print(report_color + '[ requests-responses test time ] =', request_response_total_test_time)
    print(report_color + '[ workplaces                   ] =', CNT_INSTANCES)
    print(report_color + '[ number of requests           ] =', CNT_INSTANCE_TASKS_PER_SEC, '(one workplace per second)')
    print(report_color + '[ total number of requests     ] =', len(REQUEST_TIME_LIST), '(actually sent)')
    print(responses_cnt_color + '[ total number of responses    ] =', len(RESPONSE_TIME_LIST), '(actually received)')
    print(report_color + '[ successful responses         ] =', len(RESPONSE_TIME_LIST) - CNT_ERRORS)
    print(error_color + '[ error responses              ] =', CNT_ERRORS, '(including "NotEnoughCodes")')

    if DURATION_LIST:
        print(); print(Fore.LIGHTGREEN_EX + 'Response time (including send/receive, process, queue time):')
        await display_stats(report_color, DURATION_LIST)
        print(); print(Fore.LIGHTGREEN_EX + 'Process time:')
        await display_stats(report_color, PROCESS_TIME_LIST)
        print(); print(Fore.LIGHTGREEN_EX + 'Queue time:')
        await display_stats(report_color, QUEUE_TIME_LIST)
        
        # print(); print(Fore.LIGHTGREEN_EX + 'Lists of values:')
        # print(list_title_color + '[ response time values ] =' + list_values_color, DURATION_LIST)
        # print(list_title_color + '[ response sorted values ] =' + list_values_color, sorted(DURATION_LIST))
        # print(list_title_color + '[ process time values ] =' + list_values_color, PROCESS_TIME_LIST)
        # print(list_title_color + '[ process time sorted values ] =' + list_values_color, sorted(PROCESS_TIME_LIST))
        # print(list_title_color + '[ queue time values ] =' + list_values_color, QUEUE_TIME_LIST)
        # print(list_title_color + '[ queue time sorted values ] =' + list_values_color, sorted(QUEUE_TIME_LIST))
        # print(list_title_color + '[ requests list  ] =' + list_values_color, REQUEST_TIME_LIST)
        # print(list_title_color + '[ responses list ] =' + list_values_color, RESPONSE_TIME_LIST)

    print(Style.RESET_ALL)

    errors = str()
    for e in ERRORS_LIST:
        s = f'{e[0]}  --  {e[1]}'
        errors += f'{s}\n'

    with open('test-errors-responses.txt', 'w') as f:
        f.write(errors)


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
