import logging
import botocore
import boto3
import config
from flask import render_template, Blueprint, request, redirect, session, flash
from requests import get, delete
from decorators import login_required, admin_only, reviewer_only
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger("application")
ticket_ticket_management = Blueprint('ticket_management', __name__, template_folder='templates')

def get_region():
    session = boto3.session.Session()
    aws_region = session.region_name
    return aws_region

def get_ticket_info():
    ticket_info = {}
    ddb = config.Config.TICKET_DDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(ddb)
    response = table.scan(
        FilterExpression=Attr('status').eq('Pending for review'),
    )
    return response['Items']


@ticket_ticket_management.route("/ticket/ticket_management/", methods=["GET"])
@login_required
@reviewer_only
def index():
    try:
        ticket_infos = get_ticket_info()
        return render_template("ticket/ticket_management.html", user=session["user"], ticket_infos=ticket_infos, page="ticket_ticket_management")
    except:
        flash("Unable to retrieve your ticket", "error")
        return render_template("ticket/ticket_management.html", user=session["user"], ticket_infos={}, page="ticket_ticket_management")
    return render_template("ticket/ticket_management.html")

@ticket_ticket_management.route("/ticket/ticket_management/approve", methods=["GET"])
@login_required
@reviewer_only
def approve_ticket():
    ticket_id = int(request.args.get("ticket_id", False))
    if ticket_id is False:
        return redirect("/ticket/ticket_management")

    ticket_username = request.args.get("ticket_username", False)
    if ticket_username is False:
        return redirect("/ticket/ticket_management")

    aws_region = get_region()
    sns_client = boto3.client('sns', aws_region)
    ddb = config.Config.TICKET_DDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(ddb)
    try:
        response = table.update_item(
            Key={
                'username': ticket_username,
                'id': ticket_id
            },
            UpdateExpression="set #ts=:r",
            ExpressionAttributeValues={
                ':r': 'Approved by super user'
            },
            ExpressionAttributeNames={
                "#ts": "status"
            },
            ReturnValues = "ALL_NEW"
        )
        if config.Config.TICKET_SNS_NOTIFICATION is True:
            sns_message = "Super user approved ticket. User Name:" + ticket_username + ", Title ID:" + str(ticket_id)
            # Publish a simple message to the specified SNS topic
            response = sns_client.publish(
                TopicArn=config.Config.TICKET_SNS_ADMIN_TOPIC_ARN,
                Message=sns_message,
            )
        flash(f"Approve ticket successfully in SOCA", "success")
        logger.info(f"Approve ticket id, {ticket_id}")
    except:
        flash(f"Approve ticket failed in SOCA", "error")
        logger.error(f"Approve ticket id, {ticket_id} failed")
    return redirect("/ticket/ticket_management")

@ticket_ticket_management.route("/ticket/ticket_management/reject", methods=["GET"])
@login_required
def delete_job():
    ticket_id = int(request.args.get("ticket_id", False))
    if ticket_id is False:
        return redirect("/ticket/ticket_management")

    ticket_username = request.args.get("ticket_username", False)
    if ticket_username is False:
        return redirect("/ticket/ticket_management")

    aws_region = get_region()
    sns_client = boto3.client('sns', aws_region)
    ddb = config.Config.TICKET_DDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(ddb)
    try:
        response = table.update_item(
            Key={
                'username': ticket_username,
                'id': ticket_id
            },
            UpdateExpression="set #ts=:r",
            ExpressionAttributeValues={
                ':r': 'Rejected by super user'
            },
            ExpressionAttributeNames={
                "#ts": "status"
            },
            ReturnValues = "ALL_NEW"
        )
        if config.Config.TICKET_SNS_NOTIFICATION is True:
            sns_message = "Super user rejected/closed ticket. User Name:" + ticket_username + ", Title ID:" + str(ticket_id)
            # Publish a simple message to the specified SNS topic
            response = sns_client.publish(
                TopicArn=config.Config.TICKET_SNS_ADMIN_TOPIC_ARN,
                Message=sns_message,
            )
        flash(f"Reject ticket in SOCA", "success")
        logger.info(f"Reject ticket id, {ticket_id}")
    except:
        flash(f"Reject ticket in SOCA failed", "error")
        logger.error(f"Reject ticket id, {ticket_id} failed")
    return redirect("/ticket/ticket_management")
