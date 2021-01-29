import logging
import botocore
import boto3
import config
from flask import render_template, Blueprint, request, redirect, session, flash
from requests import get, delete
from decorators import login_required, admin_only
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger("application")
ticket_ticket_management_admin = Blueprint('ticket_management_admin', __name__, template_folder='templates')

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
            FilterExpression=Attr('status').eq('Approved by super user') | Attr('status').eq('Working in progress') 
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

@ticket_ticket_management_admin.route("/ticket/ticket_management_admin/", methods=["GET"])
@login_required
@admin_only
def index():
    try:
        ticket_infos = get_ticket_info()
        closed_ticket_infos = get_closed_ticket_info()
        return render_template("ticket/ticket_management_admin.html", user=session["user"], ticket_infos=ticket_infos, closed_ticket_infos=closed_ticket_infos, page="ticket_ticket_management_admin")
    except:
        flash("Unable to retrieve ticket info", "error")
        return render_template("ticket/ticket_management_admin.html", user=session["user"], ticket_infos={}, closed_ticket_infos={}, page="ticket_ticket_management_admin")
    return render_template("ticket/ticket_management_admin.html")

@ticket_ticket_management_admin.route("/ticket/ticket_management_admin/update", methods=["POST"])
@login_required
@admin_only
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
            UpdateExpression="set #ts=:r, #u=:u",
            ExpressionAttributeValues={
                ':r': 'Working in progress',
                ':u': ticket_update
            },
            ExpressionAttributeNames={
                "#ts": "status",
                "#u": "update"
            },
            ReturnValues = "ALL_NEW"
        )
        flash(f"Approve/Update ticket successfully in SOCA", "success")
        logger.info(f"Update ticket id, {ticket_id}")
    except:
        flash(f"Approve/Update ticket in SOCA failed", "error")
        logger.error(f"Update ticket id, {ticket_id} failed")
    return redirect("/ticket/ticket_management_admin")

@ticket_ticket_management_admin.route("/ticket/ticket_management_admin/close", methods=["GET"])
@login_required
def delete_job():
    ticket_id = int(request.args.get("ticket_id", False))
    if ticket_id is False:
        return redirect("/ticket/ticket_management_admin")

    ticket_username = request.args.get("ticket_username", False)
    if ticket_username is False:
        return redirect("/ticket/ticket_management_admin")

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
                ':r': 'Closed by system admin'
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
    return redirect("/ticket/ticket_management_admin")

@ticket_ticket_management_admin.route("/ticket/ticket_management_admin/closefailed", methods=["GET"])
@login_required
def closefailed_job():
    ticket_id = int(request.args.get("ticket_id", False))
    if ticket_id is False:
        return redirect("/ticket/ticket_management_admin")

    ticket_username = request.args.get("ticket_username", False)
    if ticket_username is False:
        return redirect("/ticket/ticket_management_admin")

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
                ':r': 'Closed by system admin. Closure code unsuccessful'
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
    return redirect("/ticket/ticket_management_admin")
