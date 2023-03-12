import pandas as pd

def read_form(url_in):
    url_use = url_in.replace('/edit#gid=', '/export?format=csv&gid=')
    return pd.read_csv(url_use)

def shuffle_tasks(df):

    ## BUILD TASKS
    tasks = []
    for k in ['1', '2', '3']:
        tmp = [x for x in df['task_' + k]]
        tasks += tmp

    fail_test = True
    while fail_test:
        fail_test = False

        ## SHUFFLE TASKS
        shuffle(tasks)
        k = 0
        tasks_per_person = 3
        task_list = {}
        for n in df.name:
            per_tasks = []
            for t in range(tasks_per_person):
                per_tasks.append(tasks[k + t])
            task_list[n] = per_tasks
            k += tasks_per_person

        ## VALIDATE TASKS
        for n in task_list:
            for k in range(tasks_per_person):
                if df.loc[df.name == n, 'task_1'].values == task_list[n][k]:
                    fail_test = True
                    # print('Failed because:', n, task_list[n][k])

    return (task_list)