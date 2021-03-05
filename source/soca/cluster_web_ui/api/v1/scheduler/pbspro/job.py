import config
import subprocess
from flask import request
from flask_restful import Resource, reqparse
import logging
import base64
from decorators import private_api
from requests import get
import json
import shlex
import sys
import errors
import os
import uuid
import re
import random
import string
import shutil

logger = logging.getLogger("api")


class Job(Resource):
    @private_api
    def get(self):
        """
        Return information for a given job
        ---
        tags:
          - Scheduler
        parameters:
          - in: body
            name: body
            schema:
              optional:
                - job_id
              properties:
                job_id:
                   type: string
                   description: ID of the job
        responses:
          200:
            description: List of all jobs
          500:
            description: Backend error
        """
        parser = reqparse.RequestParser()
        parser.add_argument('job_id', type=str, location='args')
        args = parser.parse_args()
        job_id = args['job_id']
        if job_id is None:
            return errors.all_errors("CLIENT_MISSING_PARAMETER", "job_id (str) parameter is required")

        try:
            qstat_command = config.Config.PBS_QSTAT + " -f " + job_id + " -Fjson"
            try:
                get_job_info = subprocess.check_output(shlex.split(qstat_command))
                try:
                    job_info = json.loads(((get_job_info.decode('utf-8')).rstrip().lstrip()))
                except Exception as err:
                    return {"success": False, "message": "Unable to retrieve this job. Job may have terminated. Error: " + str(job_info)}, 210

                job_key = list(job_info["Jobs"].keys())[0]
                return {"success": True, "message": job_info["Jobs"][job_key]}, 200

            except Exception as err:
                return {"succes": False, "message": "Unable to retrieve Job ID (job may have terminated and is no longer in the queue)"}, 210

        except Exception as err:
            return {"success": False, "message": "Unknown error: " + str(err)}, 500

    @private_api
    def delete(self):
        """
        Delete a job from the queue
        ---
        tags:
          - Scheduler
        parameters:
          - in: body
            name: body
            schema:
              required:
                - job_id
              properties:
                job_id:
                  type: string
                  description: ID of the job to remove
        responses:
          200:
            description: Job submitted correctly
          500:
            description: Backend error
        """
        parser = reqparse.RequestParser()
        parser.add_argument('job_id', type=str, location='args')
        args = parser.parse_args()
        job_id = args['job_id']
        if job_id is None:
            return errors.all_errors("CLIENT_MISSING_PARAMETER", "job_id (str) parameter is required")

        get_job_info = get(config.Config.FLASK_ENDPOINT + "/api/scheduler/job",
                           headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY},
                           params={"job_id": job_id},
                           verify=False)

        if get_job_info.status_code != 200:
            return {"success": False, "message": "Unable to retrieve this job. Job may have terminated"}, 500
        else:
            job_info = get_job_info.json()["message"]
            job_owner = job_info["Job_Owner"].split("@")[0]
            request_user = request.headers.get("X-SOCA-USER")
            if request_user is None:
                return errors.all_errors("X-SOCA-USER_MISSING")
            if request_user != job_owner:
                return errors.all_errors("CLIENT_NOT_OWNER")
            try:
                qdel_command = config.Config.PBS_QDEL + " " + job_id
                try:
                    delete_job = subprocess.check_output(shlex.split(qdel_command))
                    return {"success": True, "message": "Job deleted"}
                except Exception as err:
                    return {"succes": False, "message": "Unable to execute qsub command: " + str(err)}, 500

            except Exception as err:
                return {"success": False, "message": "Unknown error: " + str(err)}, 500
