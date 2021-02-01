import logging
import botocore
import boto3
import datetime
import config
from flask import render_template, Blueprint, request, redirect, session, flash
from models import db, AmiList
from decorators import login_required, admin_only
from sqlalchemy import exc
from sqlalchemy.exc import SQLAlchemyError
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger("application")
ticket_support_center = Blueprint('support_center', __name__, template_folder='templates')


def get_ticket_info():
    username = get_user_name()
    ticket_info = {}
    ddb = config.Config.TICKET_DDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(ddb)
    response = table.query(
        KeyConditionExpression=Key('username').eq(username),
        FilterExpression=Attr('status').eq('Pending for review') | Attr('status').eq('Approved by super user') | Attr('status').eq('Working in progress')
    )
    return response['Items']

def get_closed_ticket_info():
    closed_ticket_info = {}
    ddb = config.Config.TICKET_DDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(ddb)
    response = table.scan(
            FilterExpression=Attr('status').eq('Closed by system admin') |Attr('status').eq('Closed by system admin. Closure code unsuccessful') | Attr('status').eq('Closed by user') | Attr('status').eq('Rejected by super user')
    )
    return response['Items']

def get_region():
    session = boto3.session.Session()
    aws_region = session.region_name
    return aws_region

def get_user_name():
    user_name = session['user']
    return user_name


@ticket_support_center.route('/ticket/support_center/', methods=['GET'])
@login_required
def index():
    ticket_infos = get_ticket_info()
    closed_ticket_infos = get_closed_ticket_info()
    user = session['user']
    return render_template('ticket/support_center.html', user = user, region_name=get_region(), ticket_infos=ticket_infos, closed_ticket_infos=closed_ticket_infos)


@ticket_support_center.route('/ticket/support_center/create', methods=['POST'])
@login_required
def ami_create():
    ticket_type = request.form.get("ticket_type")
    ticket_title = request.form.get("ticket_title")
    ticket_catalog = request.form.get("ticket_catalog")
    ticket_severity = request.form.get("ticket_severity")
    ticket_desc = request.form.get("ticket_desc")
    ticket_status = "Pending for review"
    #ticket_status_code = 2
    aws_region = get_region()
    user_name = get_user_name()
    timestamp = int(datetime.datetime.utcnow().strftime('%s'))
    ec2_client = boto3.client('ec2', aws_region)
    sns_client = boto3.client('sns', aws_region)
    ddb = config.Config.TICKET_DDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(ddb)
    try:
        response = table.put_item(
            Item={
                'id': timestamp,
                'username': user_name,
                'type': ticket_type,
                'status': ticket_status,
                #'statuscode': ticket_status_code,
                'catalog': ticket_catalog,
                'severity': ticket_severity,
                'title': ticket_title,
                'description': ticket_desc
            }
        )
        if config.Config.TICKET_SNS_NOTIFICATION is True:
            sns_message = "User " + user_name + " submits a SOCA ticket, Catalog:" + ticket_type + ", Title:" + ticket_title
            # Publish a simple message to the specified SNS topic
            response = sns_client.publish(
                TopicArn=config.Config.TICKET_SNS_TOPIC_ARN,
                Message=sns_message,
            )
        flash(f"Submit ticket successfully in SOCA", "success")
        logger.info(f"Creating ticket id")
    except:
        flash(f"Submit ticket failed in SOCA", "error")
        logger.info(f"Creating ticket id failed")
    return redirect('/ticket/support_center')

@ticket_support_center.route("/ticket/support_center/update", methods=["POST"])
@login_required
def approve_ticket():
    ticket_id = int(request.form.get("ticket_id"))
    ticket_username = request.form.get("ticket_username")
    ticket_update = request.form.get("ticket_update")
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
            UpdateExpression="set #u=:u",
            ExpressionAttributeValues={
                ':u': ticket_update
            },
            ExpressionAttributeNames={
                "#u": "userupdate"
            },
            ReturnValues = "ALL_NEW"
        )
        flash(f"Update ticket successfully in SOCA", "success")
        logger.info(f"Update ticket id, {ticket_id}")
    except:
        flash(f"Update ticket in SOCA failed", "error")
        logger.error(f"Update ticket id, {ticket_id} failed")
    return redirect("/ticket/support_center")

@ticket_support_center.route("/ticket/support_center/close", methods=["GET"])
@login_required
def delete_job():
    ticket_id = int(request.args.get("ticket_id", False))
    if ticket_id is False:
        return redirect("/ticket/support_center")

    ticket_username = request.args.get("ticket_username", False)
    if ticket_username is False:
        return redirect("/ticket/support_center")

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
                ':r': 'Closed by user'
            },
            ExpressionAttributeNames={
                "#ts": "status"
            },
            ReturnValues = "ALL_NEW"
        )
        flash(f"Close ticket in SOCA", "success")
        logger.info(f"Close ticket id, {ticket_id}")
    except:
        flash(f"Close ticket in SOCA failed", "error")
        logger.error(f"Close ticket id, {ticket_id} failed")
    return redirect("/ticket/support_center")

