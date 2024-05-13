import sys, asyncio, random, time, websockets, json, logging, os, configparser
from colorama import just_fix_windows_console, Fore, Back, Style
from pathlib import Path

just_fix_windows_console()

config = configparser.ConfigParser()
config_file = os.path.join(Path(__file__).resolve().parent, 'config.ini')
if os.path.exists(config_file):
  config.read(config_file, encoding='utf-8')
else:
  print("error! config file doesn't exist"); sys.exit()


def get_code_list():
    # gets list of code from outer source/file
    code_list = ['4680648061203', '4680648061200', ]
    return code_list


# logger = logging.getLogger('websockets')
# logger.setLevel(logging.DEBUG)
# logger.addHandler(logging.StreamHandler())

CHECK_AUTH = config.getboolean('default', 'check_auth')
PASS_IF_TASK_ERROR = config.getboolean('default', 'pass_if_task_error')
INSTANCES_COLORS_ENABLED = config.getboolean('default', 'instances_colors_enabled')
CNT_INSTANCES = int(config['default']['cnt_instances'])
CNT_TASKS = int(config['default']['cnt_tasks'])
CNT_CYCLES = int(config['default']['cnt_cycles'])
REQUEST_CYCLE_FREQUENCY = int(config['default']['request_cycle_frequency'])  # seconds

TOKEN = config['default']['token']
URI = config['default']['uri']
PROTOCOL_GUID = config['default']['protocol_guid']
ORDER_GUID = config['default']['order_guid']
STATISTIC = config.getboolean('default', 'statistic')

COLOR_SET = {
    1: Fore.YELLOW,
    2: Fore.CYAN,
    3: Fore.LIGHTGREEN_EX,
}
CNT_INSTANCES_STARTED = int()
CYCLE_START_TIME = {}
CNT_ERRORS = int()
DURATION_LIST = list()
CODE_LIST = get_code_list()


async def display_instance_text(instance_id, instance_color, text_to_display):
    # display text of particular instance
    print(instance_color + f'instance [#{instance_id}]:  ' + text_to_display)


async def receive_response(ws, instance_id, instance_color, cnt_tsks):
    # receives all responses for instance
    global CNT_ERRORS

    for cycle in range(CNT_CYCLES):
        for i in range(cnt_tsks):
            #await asyncio.sleep(2) ######################
            response = await ws.recv()
            response_time = time.monotonic()
            text_msg = f'[ response ]:  from {CYCLE_START_TIME[instance_id][cycle]} to {response_time}  --  {response}'
            await display_instance_text(instance_id, instance_color, text_msg)
            if 'Error' in response:
                CNT_ERRORS += 1
                if PASS_IF_TASK_ERROR:
                    continue
            duration = round((response_time - CYCLE_START_TIME[instance_id][cycle]), 3) 
            DURATION_LIST.append(duration)
        

async def create_request(ws, instance_id, instance_color, cnt_tsks):
    # creates all requests for instance
    json_msg = { "Operation": "PrintLabel", "Data": {
                "Code": '', "ProtocolGUID": PROTOCOL_GUID, "OrderGUID": ORDER_GUID, "Statistic": STATISTIC, } }
    CYCLE_START_TIME[instance_id] = {}


    for cycle in range(CNT_CYCLES):

        for i in range(cnt_tsks):
            # each iteration chooses random code from code_list
            code = random.choice(CODE_LIST)
            json_msg['Data']['Code'] = code
            msg = json.dumps(json_msg)

            await ws.send(msg)
            request_time = time.monotonic()
            text_msg = f'[ request ]:  {request_time}  {msg}'
            await display_instance_text(instance_id, instance_color, text_msg)

        turn_time = time.monotonic()
        text_msg = f'turn {cycle+1} tasks created  {turn_time}'
        await display_instance_text(instance_id, instance_color, text_msg)
        CYCLE_START_TIME[instance_id][cycle] = turn_time

        await asyncio.sleep(REQUEST_CYCLE_FREQUENCY)


async def instance_action_v1():
    # runs instance and its tasks
    global CNT_INSTANCES_STARTED
    CNT_INSTANCES_STARTED += 1
    instance_id = CNT_INSTANCES_STARTED
    instance_color = COLOR_SET[instance_id] if INSTANCES_COLORS_ENABLED else Fore.WHITE
    
    await display_instance_text(instance_id, instance_color, 'instance is created')
    await display_instance_text(instance_id, instance_color, 'set connection...')
    async with websockets.connect(uri=URI, subprotocols=['chat',]) as ws:
        await display_instance_text(instance_id, instance_color, 'ok. connected')

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
            asyncio.create_task( create_request(ws, instance_id, instance_color, CNT_TASKS) ),
            asyncio.create_task( receive_response(ws, instance_id, instance_color, CNT_TASKS) ),
        )

    await asyncio.sleep(0.5)
    await display_instance_text(instance_id, instance_color, 'all tasks is completed')
    

async def display_report(test_duration):
    # creates and displays a report
    print(Style.RESET_ALL)
    report_color = Fore.LIGHTMAGENTA_EX
    print(report_color + '*****************         PROGRESS REPORT        *****************')
    print(report_color + '[                 Total test time               ] =', test_duration, 'seconds')
    print(report_color + '[                   Workplaces                  ] =', CNT_INSTANCES)
    print(report_color + '[ Number of requests (one workplace per second) ] =', CNT_TASKS)
    print(report_color + '[            Number of requests (total)         ] =', CNT_INSTANCES * CNT_TASKS * CNT_CYCLES) 
    print(report_color + '[            Number of error responses          ] =', CNT_ERRORS)
    if DURATION_LIST:
        print(report_color + '[               Response time (MIN)             ] =', min(DURATION_LIST), 'seconds')
        print(report_color + '[               Response time (MAX)             ] =', max(DURATION_LIST), 'seconds')
        print(report_color + '[               Response time (AVG)             ] =', 
              round(sum(DURATION_LIST)/len(DURATION_LIST), 3), 'seconds')
    print(Fore.LIGHTCYAN_EX + '[               Response time list              ] =', DURATION_LIST)
    print(Style.RESET_ALL)


async def main():
    # the main entry function - runs setted number of instances and its tasks
    start_test_time = time.monotonic()
    await asyncio.gather( *( instance_action_v1() for i in range(CNT_INSTANCES) ) )
    finish_test_time = time.monotonic()
    test_duration = round( (finish_test_time - start_test_time), 3)
    await display_report(test_duration)



if __name__ == '__main__':
    asyncio.run(main())
