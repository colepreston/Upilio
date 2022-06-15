#(C) 2022 Nexus Technology Partners, LLC <donnykapic@ntpfw.com>
#
# This script utilizes the webhook api calls from sharefile.
#
# To make new webhook subscription, run from terminal:  python3 subscribe.py "fo123456-1234-1234-123456790"

import requests
import re
import sys
import os
import http.client as httplib
import json
import configparser
from pprint import pprint

session = requests.Session()

def authenticate(hostname, client_id, client_secret, username, password):
    uri_path = '/oauth/token'

    headers = {'Content-Type':'application/x-www-form-urlencoded'}
    params = {'grant_type':'password', 'client_id':client_id, 'client_secret':client_secret, 'username':username, 'password':password}

    url = "https://"+hostname+uri_path
    session.headers = headers
    session.params = params


    response = session.post(url, params)

    print("Authentication".ljust(PADDING), response.status_code, response.reason)
    token = None
    if response.status_code == 200:
        token = response.json()

    return token

def get_authorization_header(token):
    return {'Authorization':'Bearer %s'%(token['access_token'])}

def get_hostname(token):
    return '%s.sf-api.com'%(token['subdomain'])

# Returns record from configuration file
def getConf(section, record):
    config = configparser.ConfigParser()
    try:
        config.read("/etc/init/soter.ini")
        record = config.get(section, record)
    except configparser.NoSectionError:
        raise ValueError('Could not open configuration file or record does not exist.')
    
    return record

# Returns # of webhook subscriptions for current user
def getWebhookCount(token):
    uri_path = '/sf/v3/WebhookSubscriptions'
    url = "https://sturgesfw.sf-api.com"+uri_path
    header = get_authorization_header(token)

    response = None
    try:
        response = session.get(url, headers=header)
    except Exception as e:
        print(e)

    if response:
        response = response.json()
        #print("Webhook Count".ljust(PADDING), response['odata.count'])

        return response['odata.count']

# Create webhook subscription for given folder ID
def subscribe(token, folderID):
    uri_path = '/sf/v3/WebhookSubscriptions'
    url = "https://sturgesfw.sf-api.com/sf/v3/WebhookSubscriptions"
    header = get_authorization_header(token)
    params = {"SubscriptionContext": {"ResourceType": "Folder", "ResourceId": folderID},"WebhookUrl":"https://shepherd.upilio.cloud", "Events":[{"ResourceType":"File","OperationName":"Upload"}]}

    try:
        response = requests.post(url, json = params, headers=header)
    except Exception as e:
        print(e)
        exit()

    print(response.status_code)
    return response.json()

# Return detailed info on all active webhook subscriptions
def getWebhookSubs(token):
    url = "https://sturgesfw.sf-api.com/sf/v3/WebhookSubscriptions"
    header = get_authorization_header(token)

    response = None
    try:
        response = requests.get(url, headers=header)
    except Exception as e:
        print(e)
        exit()
    
    if response:
        print("getWebhookSubs()".ljust(17), response.status_code, response.reason)
        return response.json()

def deleteWebhook(token, webhookID):
    url = "https://sturgesfw.sf-api.com/sf/v3/WebhookSubscriptions(%s)"%webhookID
    header = get_authorization_header(token)
    
    response = None
    try:
        response = session.delete(url, headers = header)
    except Exception as e:
        print(e)
        exit()

    if response.status_code == 200:
        print(response.status_code, response.reason)
        return response

# Take folderID and return its name
# Used by getTreeView()
def getFolderNameFromID(token, folderID):
    if not folderID.startswith('fo'):
        return ''

    uri_path = "/sf/v3/Items({})?includeDeleted=false".format(folderID)
    url = "https://" + get_hostname(token) + uri_path
    header = get_authorization_header(token)
    response = session.get(url, headers=header, verify=True)
    response = response.json()
    
    return response['Name']

# Returns alphabetized list of each active webhook
def getWebhookNames(token):
    response = getWebhookSubs(token)
    print("Fetching...")
    print("Estimated wait time: 15s")
    pathList = []
    j=0
    for i in response["value"]:
        folderID = response["value"][j]["SubscriptionContext"]["ResourceId"]
        path = getTreeView(token, folderID)
        folderName = getFolderNameFromID(token, folderID)
        path = path + "/" + folderName
        pathList.append(path)
        j+=1
    
    pathList.sort()

    return pathList

# Returns SF file path of a given ID
# Used by getWebhookNames()
def getTreeView(token, itemID):
    uri_path = "/sf/v3/Items({})?treemode=copy&sourceID={}&canCreateRootFolder=false".format(itemID,itemID)
    url = "https://"+get_hostname(token)+uri_path
    header = get_authorization_header(token)
    response = session.get(url, headers=header, verify=True)
    response = response.json()
    response = response['Path'].split('/')

    pathList = []
    for i in response:
        pathList.append(getFolderNameFromID(token, i))
    pathList = list(filter(None, pathList))
    pathList.pop(0)
    path = ''
    for i in pathList:
        path += i + "/"

    return path[:-1]

# Sharefile API authentication credentials
hostname = getConf("SHAREFILE","HOSTNAME")
username = getConf("SHAREFILE","USERNAME")
password = getConf("SHAREFILE","PASSWORD")[1:-1]
client_id = getConf("SHAREFILE","CLIENT_ID") 
client_secret = getConf("SHAREFILE","CLIENT_SECRET")

PADDING=17

try:
    token = authenticate(hostname, client_id, client_secret, username, password)
except Exception as e:
    print("No token.\n")
    sys.exit()

if token:
    # this comment means nothing
    pathList = getWebhookNames(token)
    count = getWebhookCount(token)

    print("\n{} Active Webhooks".format(count))
    for i in pathList:
        print(i)
    
    '''
    currentWebhookCount = getWebhookCount(token)
    
    try:
        arg = sys.argv[1]
        subscribe(token, arg)
    except IndexError:
        print("Missing argument")
        sys.exit()
    
    newWebhookCount = getWebhookCount(token)

    if newWebhookCount > currentWebhookCount:
        print("\nNew Webhook Subscription Created Successfully!")
    '''
