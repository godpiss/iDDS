#!/usr/bin/env python
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0OA
#
# Authors:
# - Wen Guan, <wen.guan@cern.ch>, 2023

"""
Map between jobs and events
"""


import os
import pickle


class DomaEventMapJob(object):
    def __init__(self, task_name, name, events, terminated_status=['finished', 'failed', 'missing']):
        self.task_name = task_name
        self.name = name
        self.events = events
        self.terminated_status = terminated_status
        self.event_deps = {}
        self.event_status = {}

    def construct_event_dependencies(self, job_event_map):
        for event_index in self.events:
            self.event_deps[event_index] = []
            job = self.events[event_index]
            deps = job.deps
            for dep in deps:
                # dep is gwjob
                event_dep = job_event_map[dep.name]
                self.event_deps[event_index].append(event_dep)

    def set_event_status(self, event_index, status, reported):
        self.event_status[str(event_index)] = {'status': status, 'reported': reported}

    def set_event_failed(self, event_index, reported=False):
        self.set_event_status(event_index, 'failed', reported)

    def set_event_finished(self, event_index, reported=False):
        self.set_event_status(event_index, 'finished', reported)

    def set_event_missing(self, event_index, reported=False):
        self.set_event_status(event_index, 'missing', reported)

    def get_events_to_report(self):
        to_report = {}
        for event_index in self.event_status:
            event_status = self.event_status[event_index]
            if not event_status['reported']:
                to_report[event_index] = event_status['status']
        return to_report

    def acknowledge_event_report(self, report):
        for event_index in report:
            self.event_status[str(event_index)]['reported'] = True

    def get_event(self, event_index):
        event_index_str = str(event_index)
        event = self.events.get(event_index_str, None)
        return event

    def is_ok_to_process_event(self, event_index):
        # when a job is released, the external dependencies should be fixed
        # (except the events which are already marked as failed in panda).
        # here we will only need to check internal dependencies
        event_index_str = str(event_index)
        event = self.events.get(event_index_str, None)
        if not event:
            return False

        deps = self.event_deps.get(event_index_str, [])
        for dep in deps:
            task_name = dep['group_label']
            job_name = dep['event_job']
            if task_name != self.task_name or job_name != self.name:
                # external dependency, skip
                continue
            event_dep_index = dep['event_index']
            event_dep_status = self.event_status.get(event_dep_index, {}).get('status', None)
            if not event_dep_status or event_dep_status not in self.terminated_status:
                return False
        return True


class DomaEventMapTask(object):
    def __init__(self, name):
        self.name = name
        self.jobs = {}

    def add_job(self, job):
        self.jobs[job.name] = job

    def get_job(self, job_name):
        return self.jobs.get(job_name, None)


class DomaEventMap(object):
    def __init__(self, name='doma_event_map.pickle', base_dir='./'):
        if not name:
            name = 'doma_event_map.pickle'
        self.name = name
        self.base_dir = base_dir
        self.tasks = {}

    def add_task(self, task):
        self.tasks[task.name] = task

    def get_task(self, task_name):
        return self.tasks.get(task_name, None)

    def get_path(self):
        if os.path.isabs(self.name):
            path = self.name
        else:
            if self.base_dir:
                path = os.path.join(self.base_dir, self.name)
            else:
                path = self.name
        return path

    def save(self):
        try:
            path = self.get_path()
            with open(path, 'wb') as fd:
                pickle.dump(self.tasks, fd)
        except Exception as ex:
            print(ex)
            raise Exception(ex)

    def load(self):
        try:
            path = self.get_path()
            with open(path, 'rb') as fd:
                self.tasks = pickle.load(fd)
        except Exception as ex:
            # print(ex)
            raise Exception(ex)
