import paramiko
import json
import threading
import logging
import sys
import re
import time
import redis
import datetime
import base64
import traceback
from prometheus_client import CollectorRegistry, Gauge, Enum, push_to_gateway


class MyThread(threading.Thread):
    def __init__(self, event, name, pause, **kwargs):
        threading.Thread.__init__(self)
        self.stopped = event
        self.name = name
        self.kwargs = kwargs
        self.pause = pause

    def run(self):
        start_connection(self.name, **self.kwargs)
        while not self.stopped.wait(self.pause):
            start_connection(self.name, **self.kwargs)


def substitute(data_set, file):
    """Processing files line by line and replacing env variables in placeholders {{}}"""
    with open(file, "r") as f:
        data = f.read()
        matches = [match for match in re.finditer(r'%(.*?)%', data)]
        if matches:
            for item in matches:
                try:
                    env_var = data_set[item.group(1)]
                    # logging.info('Replacing variable {} in file: {}'.format(item.group(1), file))
                    data = data.replace(item.group(), '{}'.format(env_var))
                except KeyError:
                    logging.warning('{} environment variable not found'.format(item.group(1)))
            else:
                # logging.info('DONE')
                return data
        else:
            # logging.warning('Placeholders not found')
            return data


def set_offline(name, resource):
    global status
    status[name]["status"] = "OFFLINE"
    for asset in resource["RESOURCES"]:
        status[name]['RESOURCES'][asset['name']]['status'] = "N/A"
        status[name]['RESOURCES'][asset['name']]['updated'] = datetime.datetime.now().timestamp()
        r.set(name, json.dumps(status[name]))
        metrics_exporter(asset["name"], status[name]['RESOURCES'][asset['name']]['status'], {'CPU': '0', 'RAM': '0', 'HDD': '0'}, asset["brand"])


def result_handler(data, kind, host):
    metrics = ''
    if kind == "Oracle":
        data = data.strip().split('\n')
        print(data)
        if len(data) > 1:
            metrics = data[1].strip()
        return data[0].upper(), metrics
    if kind == "Couchbase":
        try:
            data = data.split('\n')[0:3]
            i = [data[0].index('UNIT'), data[0].index('LOAD'), data[0].index('ACTIVE'), data[0].index('SUB'),
                 data[0].index('DESCRIPTION')]
        except ValueError:
            return "N/A", metrics
        return f"{data[1][i[0]:i[1]].strip()}, {data[1][i[1]:i[2]].strip()}, {data[1][i[2]:i[3]].strip()}, {data[1][i[3]:i[4]].strip()}", metrics
    if kind == "Cassandra":
        cassandra_status = {}
        data_list = [f"Datacenter: {d}\n" for d in data.split('Datacenter: ') if d]
        if data_list:
            for data in data_list:
                try:
                    datacenter = re.findall(r"(?s)(?<=Datacenter: ).*?(?=\n)", data)
                    servers = re.findall(r'(?s)(?<=Rack\n).*?(?=\n\n)', data)[0].split('\n')
                    for n in servers:
                        row = n.split()
                        cassandra_status[row[1]] = {'status': row[0], 'id': row[6], 'rack': row[7], 'datacenter': datacenter[0]}
                except IndexError:
                    traceback.print_exc()
                    return "N/A", metrics
            return cassandra_status[host], metrics
        return "N/A", metrics



def base64_encode(script):
    script_bytes = script.encode('ascii')
    base64_bytes = base64.b64encode(script_bytes)
    return base64_bytes.decode('ascii')


def metrics_to_dict(env_var):
    data_set = {}
    for match in re.finditer(r'(.*?)(: ([\s\S]*?) )', env_var):
        data_set[match.group(1)] = match.group(3)
    return data_set


def metrics_exporter(asset, status, metrics, db_type):
    g_cpu.labels(asset).set(metrics['CPU'])
    g_mem.labels(asset).set(metrics['RAM'])
    g_hdd.labels(asset).set(metrics['HDD'])
    if db_type == 'Oracle':
        g_oracle_active_users.labels(asset=asset, db_type=db_type).set(metrics.get('ACTIVE_USERS', 0))
        if status in ['STARTED', 'OPEN', 'ONLINE', 'STOPPED', 'MOUNTED', 'OFFLINE']:
            e_oracle_status.labels(asset=asset, db_type=db_type).state(status)
    push_to_gateway('10.193.1.103:9091', job='batchA', registry=registry)


def start_connection(name, **resource):
    logging.info(f'Connecting to resource: {name} ...')
    global status
    try:
        conn = paramiko.SSHClient()
        conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        conn.connect(resource["HOST"], username=resource["USER"], password=resource["PASS"], port=22)
        if conn:
            for asset in resource["RESOURCES"]:
                data_set = {**asset}
                result = execute(conn,
                                 f"bash -c 'echo {base64_encode(substitute(data_set, asset['script']))} | base64 -d > remoterun.status.sh; chmod +x remoterun.status.sh; ./remoterun.status.sh && rm ./remoterun.status.sh'")
                common_metrics = execute(conn,
                                         f"bash -c 'echo {base64_encode(substitute(data_set, 'scripts/common.sh'))} | base64 -d > remoterun.status.sh; chmod +x remoterun.status.sh; ./remoterun.status.sh && rm ./remoterun.status.sh'")
                status[name]["status"] = "ONLINE"
                print("DEBUG", asset, f"bash -c 'echo {base64_encode(substitute(data_set, asset['script']))} | base64 -d > remoterun.status.sh; chmod +x remoterun.status.sh; ./remoterun.status.sh && rm ./remoterun.status.sh'", result)
                result, db_metrics = result_handler(result, asset["brand"], resource["HOST"])
                metrics = metrics_to_dict(f"{common_metrics.strip()} {db_metrics.strip()} ")
                logging.info(f'{asset["name"]} -> STATUS: {result}')
                logging.info(f'{asset["name"]} -> METRICS: {metrics}')
                status[name]['RESOURCES'][asset['name']]['status'] = result
                status[name]['RESOURCES'][asset['name']]['updated'] = datetime.datetime.now().timestamp()
                metrics_exporter(asset["name"], result, metrics, asset["brand"])
                r.set(name, json.dumps(status[name]))
        conn.close()
    except Exception as e:
        logging.error(f"{name} -> {repr(e)}")
        traceback.print_exc()
        set_offline(name, resource)
    open('status.json', 'w').write(json.dumps(status, indent=4))


def execute(conn, cmd):
    (stdin, stdout, stderr) = conn.exec_command(cmd)
    return "{}".format(stdout.read().decode('utf-8'))


if __name__ == '__main__':
    registry = CollectorRegistry()
    g_cpu = Gauge('CPU', 'CPU precent gauge', labelnames=['asset'], registry=registry)
    g_mem = Gauge('MEM', 'MEM precent gauge', labelnames=['asset'], registry=registry)
    g_hdd = Gauge('HDD', 'HDD precent gauge', labelnames=['asset'], registry=registry)
    g_oracle_active_users = Gauge('active_users', 'Active current Oracle DB users', labelnames=['asset', 'db_type'],
                                  registry=registry)
    e_oracle_status = Enum('Asset_state', 'Description of enum',
                           states=['STARTED', 'OPEN', 'ONLINE', 'STOPPED', 'MOUNTED', 'OFFLINE'],
                           labelnames=['asset', 'db_type'], registry=registry)
    r = redis.Redis(host="redis", password="redispw", port=6379)
    logging.basicConfig(stream=sys.stderr,
                        level=logging.INFO,
                        format='[%(asctime)s]:[%(levelname)s]: %(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S')

    resources = json.loads(open("assets.json", "r").read())
    status = {}

    for resource in resources:
        status[resource] = {"HOST": resources[resource]["HOST"], "status": "N/A", "RESOURCES": {}}
        for asset in resources[resource]["RESOURCES"]:
            if asset["brand"] == "Oracle":
                path = asset.get("OGG_HOME", asset.get("ORACLE_HOME"))
                obj = ''.join(
                    [asset.get(name, '') for name in ["ORACLE_SID", "LISTENER_NAME", "INSTANCE_NAME", "CLUSTER_NAME"]])
                if obj == '':
                    obj = 'MANAGER'
                status[resource]["RESOURCES"][asset["name"]] = {
                    "brand": asset["brand"],
                    "type": asset["type"],
                    "link": asset["link"],
                    "status": asset["status"],
                    "obj": obj,
                    "path": path,
                    "updated": datetime.datetime.now().timestamp()
                }
            elif asset["brand"] == "Couchbase":
                status[resource]["RESOURCES"][asset["name"]] = {
                    "brand": asset["brand"],
                    "type": asset["type"],
                    "link": asset["link"],
                    "status": asset["status"]
                }
            elif asset["brand"] == "Cassandra":
                status[resource]["RESOURCES"][asset["name"]] = {
                    "brand": asset["brand"],
                    "type": asset["type"],
                    "link": asset["link"],
                    "status": asset["status"]
                }
        r.set(resource, json.dumps(status[resource]))
        open('status.json', 'w').write(json.dumps(status, indent=4))

    for resource in resources:
        stopFlag = threading.Event()
        thread = MyThread(stopFlag, resource, 20, **resources[resource])
        thread.start()

    while True:
        time.sleep(20)
        threads = [thread.name for thread in threading.enumerate() if thread.name in resources]
        logging.info(f"{len(threads)} of {len(resources)} status check threads are running")
        if len(threads) != len(resources):
            for resource in resources:
                if resource not in threads:
                    logging.warning(f"{resource} checking process is down. Restarting...")
                    stopFlag = threading.Event()
                    thread = MyThread(stopFlag, resource, 20, **resources[resource])
                    thread.start()
