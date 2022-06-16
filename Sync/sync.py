# (C) 2022 Nexus Technology Partners, LLC <donnykapic@ntpfw.com>
import requests
import re
import sys
import configparser
import os
import http.client as httplib
import urllib.parse as urlparse
import json
import mimetypes
import pymysql
import time
import calendar
import functools
from pprint import pprint
from datetime import datetime
from calendar import timegm

session = requests.Session()

# Read webhook header from temp file
def getHeaders():
    with open(sys.stdin, "r") as f:
        headers = f.read()
        f.close()

    return headers

# Convert given list to dictionary
def convert(listToConvert):
    it = iter(listToConvert)
    res_dct = dict(zip(it, it))

    return res_dct

def getTimestampProxy(webhook):
    timestamp = str(re.findall("[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}.[0-9]{7}Z", webhook))
    newtime = timestamp.replace(":", "_")
    newhook = re.sub("[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}.[0-9]{7}Z", newtime[2:-2], webhook)
    return newhook

# Format headers and remove unneeded characters
def cleanHeader(dirtyStr):
    charactersToRemove = "{}()[]\\\">="
    cleanStr = str(dirtyStr)

    for character in charactersToRemove:
        cleanStr = cleanStr.replace(character, "")

    cleanStr = getTimestampProxy(cleanStr)
    cleanStr = re.split('[:,]+', cleanStr)

    try:
        cleanStr[3] = cleanStr[3].replace("_",":")
    except Exception as e:
        print("Exception Triggered")
        sys.exit()

    return cleanStr

def cleanWebhook(dirtyStr):
    charactersToRemove = "{}()[]\\\">="
    cleanStr = str(dirtyStr)

    for character in charactersToRemove:
        cleanStr = cleanStr.replace(character, "")

    cleanStr = getTimestampProxy(cleanStr)
    cleanStr = re.split('[:,]+', cleanStr)
    cleanStr[15] = cleanStr[15].replace('_',':')
    
    try:
        cleanStr[15] = cleanStr[15].replace("_",":")
    except Exception as e:
        print("Exception triggered\n")
        sys.exit()

    return cleanStr

def retry(url, payload, headers, requestObject):
    numTries = 3
    while(numTries > 0 and requestObject.status_code != 200):
        requestObject = requests.post(url, data = payload, headers = headers)
        numTries -= 1

    print(requestObject.status_code)

def getData():
    catString = ""
    for line in sys.stdin:
        catString += line
    return catString

def getConf(section, record):
    config = configparser.ConfigParser()
    try:
        config.read("/etc/init/soter.ini")
        record = config.get(section, record)
    except configparser.NoSectionError:
        raise ValueError('Could not open configuration file or record does not exist.')
        exit()

    return record

def logger(fileName, content):
    try:
        f = open("private/"+fileName, "a")
    except Exception as e:
        print(str(e))
        sys.exit()

    f.write(str(content) + "\n")
    f.close()

def proxy():
    webhook = getData()
    # Separate webhook into 2 lists: headers & payload
    webhook = webhook.splitlines()
    # Parse headers from webhook & convert headers list to dict
    headers = webhook[0]
    headers = cleanheader(headers)
    headers = convert(headers)
    
    # Parse JSON payload from webhook
    try:
        payload = webhook[2]
        payload = cleanWebhook(payload)
        payload = convert(payload)
    except IndexError as e:
        logger("Error_log.txt", str(e))
        sys.exit()
    
    # Send webhook to the url
    try:
        url = getConf("SectionOne" "URL")
        r = requests.post(url, data=paload, headers=headers, verify="/etc/ssl/certs")
        if r.status_code == 200:
            return 1
    except requests.exceptions.Timeout:
        # Retry max 3 times
        retry(url, payload, headers)
    except requests.exceptions.RequestException as e:
        # Fatal error
        sys.exit()

# proxy functions
##################################################################
# sync functions

def authenticate(hostname, client_id, client_secret, username, password):
    uri_path = '/oauth/token'
    headers = {'Content-Type':'application/x-www-form-urlencoded'}
    params = {'grant_type':'password', 'client_id':client_id, 'client_secret':client_secret,
            'username':username, 'password':password}

    url="https://"+hostname+uri_path
    session.headers=headers
    session.params=params
    try:
        response = requests.post(url, params)
    except Exception as e:
        print(e)
    
    sts_code = response.status_code
    rsn = response.reason

    print("Authentication".ljust(17), response.status_code, response.reason)
    
    token = None
    if response.status_code == 200:
        token = response.json()

    return token

def get_authorization_header(token):
    return {'Authorization':'Bearer %s'%(token['access_token'])}

def get_hostname(token):
    return '%s.sf-api.com'%(token['subdomain'])

def get_root(token, get_children=True):
    uri_path = '/sf/v3/Items'
    if get_children:
        uri_path+='?$expand=Children'
    url = "https://"+get_hostname(token)+uri_path
    header=get_authorization_header(token)

    response=session.get(url,headers=header,verify=True)
    items = response.json()
    
    if 'Children' in items:
        children = items['Children']
        #print(children)
        return(children)

def get_folder_with_query_parameters(token, item_id):
    uri_path = '/sf/v3/Items(%s)?$expand=Children&$select=Id,Name,Children/Id,Children/Name,Children/CreationDate'%(item_id)
    url= "https://"+get_hostname(token)+uri_path
    response = session.get(url, headers = get_authorization_header(token))
    items = response.json()

    if 'Children' in items:
        children = items['Children']
        #for child in children:
            #print(child['Name'], child['Id'])

    return children

def download_item(token, item_id, savePath):
    #print("Downloading File: {}".format(deviceName))
    uri_path = '/sf/v3/Items(%s)/Download'%(item_id)
    http = httplib.HTTPSConnection(get_hostname(token))
    http.request('GET', uri_path, headers=get_authorization_header(token))
    response = http.getresponse()
    location = response.getheader('location')
    redirect = None
    if location:
        redirect_uri = urlparse.urlparse(location)
        redirect = httplib.HTTPSConnection(redirect_uri.netloc)
        redirect.request('GET', '%s?%s'%(redirect_uri.path, redirect_uri.query))
        response = redirect.getresponse()
    
    try:
        #with open(imagePath, 'wb') as target:
        with open(savePath, 'wb') as target:
            b = response.read()
            target.write(b)
    except FileNotFoundError:
        print("ERROR: Could not write to {}".format(savePath))
        sys.exit()

    #print("Download".ljust(17), response.status, response.reason)
    http.close()
    if redirect:
        redirect.close()

def getTreeView(token, itemID):
    uri_path = "/sf/v3/Items({})?treemode=copy&sourceID={}&canCreateRootFolder=false".format(itemID,itemID)
    url = "https://"+get_hostname(token)+uri_path
    header = get_authorization_header(token)
    response = session.get(url,headers=header,verify=True)
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

def getFolderNameFromID(token, folderID):
    if not folderID.startswith('fo'):
        return ''
    
    uri_path = "/sf/v3/Items({})?includeDeleted=false".format(folderID)
    url = "https://"+get_hostname(token)+uri_path
    header = get_authorization_header(token)
    response = session.get(url,headers=header,verify=True)
    response = response.json()
    
    return response['Name']

def getFolderID(webhook):
    folderID = str(re.findall("fo[a-z0-9]{6}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}", webhook))[2:-2]
    return folderID

def getFileID(webhook):
    fileID = str(re.findall("fi[a-z0-9]{6}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}", webhook))[2:-2]
    return fileID

def getTimestamp(webhook):
    timestamp = str(re.findall("Timestamp=[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}%3A[0-9]{2}%3A[0-9]{2}.[0-9]{7}Z", webhook))[12:-11]
    timestamp = timestamp.replace("%3A",":")
    timestamp += "Z"
    return timestamp

def clean(dirtyStr):
    cleanStr = str(dirtyStr).replace(',','')
    cleanStr = cleanStr.replace('(','')
    cleanStr = cleanStr.replace(')','')
    return cleanStr


def download_image(token, folderID, fileID, path):
    rootFolder = get_root(token, 1)
    for root in rootFolder:
        upilioContents = get_folder_with_query_parameters(token, root['Id'])
        for child in upilioContents:
            if child['Name'] in path:
                folderContents = get_folder_with_query_parameters(token, child['Id'])
                for child in folderContents:
                    if child['Id'] in folderID:
                        folderContents = get_folder_with_query_parameters(token, child['Id'])
                        for child in folderContents:
                            if child['Id'] in fileID:
                                deviceName = child['Name'][:-4]
                                savePath = path + "/" + child['Name']
                                print("Save Path".ljust(17), savePath)
                                download_item(token, fileID, savePath)

                                return deviceName

# Take UTC timestamp and convert to time since epoch
def getEpochTime(timestamp):
    #print("getEpochTime(): {}".format(timestamp.rjust(10)))
    timestamp = time.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%fZ")
    epochTime = timegm(timestamp)
    return epochTime

def dbQuery(query, db_host, db_user, db_password, database):
    db = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=database)
    cursor = db.cursor()
    cursor.execute(query)
    db.commit()
    result = cursor.fetchall()
    return result

def existsInDB(path, db_host, db_user, db_password, database):
    result = dbQuery("SELECT DeviceName FROM AgentReports WHERE DeviceName = '{}' limit 1".format(path),db_host,db_user,db_password,database)
    if result is None or len(result) == 0:
        return False
    else:
        return True

def checkStatus(interval, avgReportingInterval, stddev, nowTime, deviceName):
    lowerRange = avgReportingInterval - round(stddev/2)
    upperRange = avgReportingInterval + round(stddev/2)
    firstStandardDev = range(lowerRange, upperRange)
    
    if interval in firstStandardDev:
        return "On Time"
    else:
        lowerRange = avgReportingInterval - round(stddev)
        upperRange = avgReportingInterval + round(stddev)
        secondStandardDev = range(lowerRange, upperRange)
        
        if interval in secondStandardDev:
            if interval < avgReportingInterval:
                return "Early"
            elif interval > avgReportingInterval:
                return "Late"
        else:
            return "Offline"

def makeJson(deviceName, path, status, db_host, db_user, db_password, database):
    # Get yellow and red time from database
    db = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=database)
    cursor = db.cursor()
    cursor.execute("SELECT YellowTime,RedTime FROM ExpirationDates WHERE DeviceName='{}'".format(deviceName))
    db.commit()
    result = list(cursor.fetchall()[0])
    yellowTime = result[0]
    redTime = result[1]

    #Send relevant info
    params = {"DeviceName":deviceName,"Path":path,"Status":status,"YellowTime":yellowTime,"RedTime":redTime}
    return params

def sync():
    print("Synchronizing")
    # Sharefile API
    hostname = getConf("SHAREFILE","HOSTNAME")
    username = getConf("SHAREFILE","USERNAME")
    password = getConf("SHAREFILE","PASSWORD")[1:-1]
    client_id = getConf("SHAREFILE","CLIENT_ID")
    client_secret = getConf("SHAREFILE","CLIENT_SECRET")
    
    # MySQL
    db_host = getConf("DB","HOST")
    db_user = getConf("DB","USER")
    db_password = getConf("DB","DB_PASSWORD")[1:-1]
    database = getConf("DB","DATABASE")

    # Get webhook
    webhook = getData()
    folderID = getFolderID(webhook)
    fileID = getFileID(webhook)
    STimestamp = round(getEpochTime(getTimestamp(webhook)))
    nowTime = round(time.time())
    
    # Authenticate through sharefile api
    try:
        token = authenticate(hostname,client_id,client_secret,username,password)
    except Exception as e:
        print("Unable to authenticate through ShareFile API\n")
        sys.exit()
    
    if token:
        # Get file path and file name from Sharefile
        path = getTreeView(token, fileID)
        deviceName = download_image(token, folderID, fileID, path)
        print("Name".ljust(17), deviceName)
        if deviceName is None:
            print("Download failed.\n")
            sys.exit()
        
        #First entry for a given device
        if not existsInDB(deviceName,db_host,db_user,db_password,database):
            print("New database entry".ljust(17), path)
            dbQuery("INSERT INTO AgentReports (STimestamp, DeviceName, Path, NowTimestamp, ReportingInterval, AvgReportingInterval, SD1, SD2, Status) VALUES ({}, '{}', '{}', {},{},{},{},{},'{}')".format(STimestamp,deviceName,path,nowTime,0,0,0,0,'Offline'),db_host,db_user,db_password,database)
            sys.exit()

        # Retrieve info from db for calculations
        db = pymysql.connect(
                host=db_host,
                user=db_user,
                password=db_password,
                database=database)
        cursor = db.cursor()
        cursor.execute("SELECT (SELECT NowTimestamp FROM AgentReports WHERE DeviceName = '{}' ORDER BY NowTimestamp DESC LIMIT 1) AS nowTime, (SELECT AVG(ReportingInterval) FROM AgentReports WHERE DeviceName = '{}') AS average, (SELECT STDDEV(ReportingInterval) FROM AgentReports WHERE DeviceName = '{}') AS stddev".format(deviceName,deviceName,deviceName))
        db.commit()
        result = list(cursor.fetchall()[0])
        prevTime = result[0]
        avgReportingInterval = result[1]
        stddev = result[2]
        
        # Calculate report interval
        prevTime = clean(prevTime)
        if len(prevTime) == 0:
            prevTime = nowTime - 600
        interval = int(nowTime) - int(prevTime)
        
        # Formatting
        avgReportingInterval = int(float(clean(avgReportingInterval)))  
        stddev = int(float(clean(stddev)))                              
        stddev2 = stddev + avgReportingInterval                         
        
        # Determine device status
        status = checkStatus(interval, avgReportingInterval, stddev, nowTime, deviceName)
        
        # Update table
        dbQuery("INSERT INTO AgentReports (STimestamp,DeviceName,Path,NowTimestamp,AvgReportingInterval,ReportingInterval,SD1,SD2,Status) values({},'{}','{}',{},{},{},{},{},'{}')".format(STimestamp,deviceName,path,nowTime,avgReportingInterval,interval,stddev,stddev2,status),db_host,db_user,db_password,database)
        
        # Create json object to send to socket io
        jsonObj = makeJson(deviceName, path, status, db_host, db_user, db_password, database)
        if "Cameras" in path:
            print("JSON Object")
            pprint(jsonObj)
        else:
            print("Type:".ljust(17), "Screens")

job = getConf("WHATISMYPURPOSE","JOB")

if job == "PassTheButter":
    print("Dear god.")
elif job == "PROXY":
    proxy()
elif job == "SYNC":
    sync()

print("***********************************************")


