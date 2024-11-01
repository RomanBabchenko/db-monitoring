from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
import redis
import json
from datetime import datetime


# Create your views here.
class IndexView(View):
    def get(self, request, *args, **kwargs):
        return render(request, "dashboard.html")


class DashboardViewOracle(View):
    def get(self, request, *args, **kwargs):
        return render(request, "dashboard.html")

    def get_data(request):
        """Returns grouped data from CRM"""
        r = redis.Redis(host="redis", password="redispw", port=6379)
        result = []
        for key in r.scan_iter("*"):
            resource = json.loads(r.get(key).decode('utf-8'))
            for asset in resource["RESOURCES"]:
                if resource["RESOURCES"][asset]["brand"] == "Oracle":
                    row = {
                        "node": key.decode('utf-8'),
                        "ip": resource["HOST"],
                        "state": resource["status"],
                        "name": asset,
                        "type": resource["RESOURCES"][asset]["type"],
                        "status": resource["RESOURCES"][asset]["status"],
                        "obj": resource["RESOURCES"][asset]["obj"],
                        "path": resource["RESOURCES"][asset]["path"],
                        "link": resource["RESOURCES"][asset]["link"],
                        "updated": datetime.fromtimestamp(resource["RESOURCES"][asset]["updated"])
                    }
                    result.append(row)
        return JsonResponse(result, safe=False)


class DashboardViewCouchbase(View):
    def get(self, request, *args, **kwargs):
        return render(request, "dashboard.html")

    def get_data(request):
        """Returns grouped data from CRM"""
        r = redis.Redis(host="redis", password="redispw", port=6379)
        result = []
        for key in r.scan_iter("*"):
            resource = json.loads(r.get(key).decode('utf-8'))
            for asset in resource["RESOURCES"]:
                if resource["RESOURCES"][asset]["brand"] == "Couchbase":
                    status = resource["RESOURCES"][asset]["status"].split(', ')
                    try:
                        unit = status[0]
                        load = status[1].upper()
                        active = status[2].upper()
                        sub = status[3].upper()
                    except IndexError:
                        unit, load, active, sub = "N/A", "N/A", "N/A", "N/A"
                    row = {
                        "node": key.decode('utf-8'),
                        "ip": resource["HOST"],
                        "state": resource["status"],
                        "name": asset,
                        "type": resource["RESOURCES"][asset]["type"],
                        "unit": unit,
                        "load": load,
                        "active": active,
                        "sub": sub,
                        "link": resource["RESOURCES"][asset]["link"],
                        "updated": datetime.fromtimestamp(resource["RESOURCES"][asset]["updated"])
                    }
                    result.append(row)
        return JsonResponse(result, safe=False)

class DashboardViewCassandra(View):
    def get(self, request, *args, **kwargs):
        return render(request, "dashboard.html")

    def get_data(request):
        """Returns grouped data from CRM"""
        r = redis.Redis(host="redis", password="redispw", port=6379)
        result = []
        status_dict = {
            "U": "UP",
            "D": "DOWN",
        }
        state_dict = {
            "N": "NORMAL",
            "L": "LEAVING",
            "J": "JOINING",
            "M": "MOVING"
        }
        for key in r.scan_iter("*"):
            resource = json.loads(r.get(key).decode('utf-8'))
            for asset in resource["RESOURCES"]:
                if resource["RESOURCES"][asset]["brand"] == "Cassandra":
                    status = resource["RESOURCES"][asset]["status"]
                    print(status)
                    try:
                        node_status = status_dict[status['status'][0]]
                        node_state = state_dict[status['status'][1]]
                        datacenter = status['datacenter']
                        rack = status['rack']
                    except (IndexError, TypeError):
                        node_status, node_state, datacenter, rack = "N/A", "N/A", "N/A", "N/A"
                    row = {
                        "node": key.decode('utf-8'),
                        "ip": resource["HOST"],
                        "state": resource["status"],
                        "name": asset,
                        "type": resource["RESOURCES"][asset]["type"],
                        "node_status": node_status,
                        "node_state": node_state,
                        "datacenter": datacenter,
                        "rack": rack,
                        "link": resource["RESOURCES"][asset]["link"],
                        "updated": datetime.fromtimestamp(resource["RESOURCES"][asset]["updated"])
                    }
                    result.append(row)
        return JsonResponse(result, safe=False)