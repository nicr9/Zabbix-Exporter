#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import time
from prometheus_client import start_http_server, Gauge, Summary
from prometheus_client.core import REGISTRY
from pyzabbix import ZabbixAPI


class TriggerCollector(object):
    def __init__(self, url, username, password):
        self.zapi = ZabbixAPI(url)
        self.zapi.login(username, password)

        # Create metric objs
        self.trigger_state = Gauge('zabbix_trigger_state', 'Zabbix Trigger value (ok=0, problem=1)')

    def collect(self):
        # Get a list of all triggers
        triggers = self.zapi.trigger.get(
                                    monitored=1,
                                    active=1,
                                    output='extend',
                                    expandDescription=1,
                                    selectHosts=['host'],
                                    )

        for t in triggers:
            t['value']
            for host in t['hosts']:
                self.trigger_state.set(t['value'], labels={
                    'host': host['host'],
                    'trigger': t['description'],
                    'triggerid': t['triggerid'],
                    'templateid': t['templateid'],
                    })

        yield self.trigger_state


class EventCollector(object):
    def __init__(self, url, username, password):
        self.zapi = ZabbixAPI(url)
        self.zapi.login(username, password)

        self.last_collection = int(time.time())

        # Create metric objs
        self.event_duration = Summary('zabbix_event_duration', 'Summary of Zabbix event resolution duration')

    def collect(self):
        # Get a list of all events with value=OK
        ok_events = self.zapi.event.get(
                                    value=0,
                                    time_from=self.last_collection,
                                    output='extend',
                                    selectHosts=['host'],
                                    sortfield='clock',
                                    )
        self.last_collection = int(time.time())

        # Determine the corresponding problem events
        p_ids = []
        events = defaultdict({})
        for ok in ok_events:
            p_ids.append(ok['c_eventid'])
            events[ok['eventid']]['end'] = ok['clock']
            events[ok['eventid']]['hosts'] = ok['hosts'][0]['host']
            events[ok['eventid']]['template'] = ok['objectid']

        problem_events = self.zapi.event.get(
                                    eventids=p_ids,
                                    output='extend',
                                    )
        for prob in problem_events:
            events[prob['r_eventid']]['start'] = ok['clock']

        for event in sorted(events, key=lambda x: x['end']):
            duration = event['end'] - event['start']
            self.event_duration.observe(duration, labels={
                'host': host['host'],
                'templateid': t['templateid'],
                })

        yield self.event_duration


def main():
    # Config as environment variables
    url = os.environ.get('ZABBIX_EXP_URL', 'http://localhost/')
    username = os.environ.get('ZABBIX_EXP_USERNAME', 'Admin')
    password = os.environ.get('ZABBIX_EXP_PASSWORD', 'zabbix')

    triggers = TriggerCollector(url, username, password)
    events = EventCollector(url, username, password)

    try:
        # Start the webserver on the required port
        start_http_server(9288)
        REGISTRY.register(triggers)
        REGISTRY.register(events)
    except KeyboardInterrupt:
        print("Keyboard Interrupted")
        exit(0)


if __name__ == "__main__":
    main()
