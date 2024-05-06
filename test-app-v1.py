import asyncio
import random, time
from colorama import just_fix_windows_console
from colorama import Fore, Back, Style

just_fix_windows_console()

COLOR_SET = {
    1: Fore.GREEN,
    2: Fore.YELLOW,
    3: Fore.CYAN,
}
CNT_INSTANCES = 3
CNT_INSTANCES_STARTED = int()
CNT_REQUESTS = 3


async def instance_task(instance_id, instance_color, task_id):
    #
    start_time = time.monotonic()

    task_time = random.randint(1, 5)
    print(instance_color + f'instance [#{instance_id}]:  ' + 
          f'task [#{task_id}] has started' + 
          f' with duration time [{task_time} seconds]')
    await asyncio.sleep(task_time)

    finish_time = time.monotonic()
    duration = round((finish_time - start_time), 3)
    print(instance_color + f'object [{instance_id}]:  ' + 
          f'task [#{task_id}] has completed in [{duration} seconds]')


async def instance_action_v1():
    # run instance and its tasks
    global CNT_INSTANCES_STARTED
    CNT_INSTANCES_STARTED += 1
    instance_id = CNT_INSTANCES_STARTED
    instance_color = COLOR_SET[instance_id]
    
    print(instance_color + f'instance [#{instance_id}] is created')
    
    # runs instanse's tasks
    await asyncio.gather( *( asyncio.create_task( instance_task(instance_id, instance_color, i) ) 
                            for i in range(1, CNT_REQUESTS) ) )

    await asyncio.sleep(0.5)
    print(instance_color + f'instance [#{instance_id}]:  ' + f'all tasks is completed')
    

async def main():
    # the main entry function
    # runs setted number of instances and its tasks
    await asyncio.gather( *( instance_action_v1() for i in range(CNT_INSTANCES) ) )
    print(Style.RESET_ALL)


if __name__ == '__main__':
    asyncio.run(main())
