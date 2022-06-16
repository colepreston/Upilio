import json
import http.client as httplib
import os
import mimetypes
import time
import urllib.parse as urlparse
import shutil
import requests
import configparser
import sys
from datetime import datetime
import pyautogui
import subprocess
import csv

session = requests.Session()

def authenticate(hostname, client_id, client_secret, username, password):
    uri_path = '/oauth/token'
    
    headers = {'Content-Type':'application/x-www-form-urlencoded'}
    params = {'grant_type':'password', 'client_id':client_id, 'client_secret':client_secret,
              'username':username, 'password':password}
              
    url="https://"+hostname+uri_path
    session.headers=headers
    session.params=params
    response = requests.post(url,params)
    
    status_code = response.status_code
    reason = response.reason
    
    log.write(str(status_code))
    log.write(str(reason))
    
    token = None
    if response.status_code == 200:
        token = response.json()
    
    return token

def get_authorization_header(token):
    return {'Authorization':'Bearer %s'%(token['access_token'])}
    
def get_hostname(token):
    return '%s.sf-api.com'%(token['subdomain'])

def get_root(token, get_children=True):
    uri_path = '/sf/v3/Items(allshared)'
    if get_children:
        uri_path+='?$expand=Children'
    url = "https://"+get_hostname(token)+uri_path
    header=get_authorization_header(token)

    
    response=session.get(url,headers=header,verify=True)
    items = response.json()
    if 'Children' in items:
        children = items['Children']
        #print(children)
        return children
        
def upload_file(token, folder_id, localPath):
    uri_path = '/sf/v3/Items(%s)/Upload'%(folder_id)
    http = httplib.HTTPSConnection(get_hostname(token))
    try:
        http.request('GET', uri_path, headers=get_authorization_header(token))
    except Exception as e:
        sys.exit()
    
    response = http.getresponse()
    upload_config = response.read()
    temp = upload_config.decode()
    temp_2 = json.loads(temp)


    if 'ChunkUri' in temp_2:
        try:
            upload_response = multipart_form_post_upload(temp_2['ChunkUri'], localPath)
        except Exception as e:
            sys.exit()
        print(upload_response.status, upload_response.reason)
        if upload_response.status!=200:
            raise ValueError('Received Response Status: '+str(upload_response.status)+ ' ' + str(upload_response.reason)+
                             '. \r\n Expected 200 OK!')
            return 0
        else:
            return upload_response.status
    else:
        print('No Upload URL received')
        return 0
        
def multipart_form_post_upload(url, filepath):
    newline = b'\r\n'
    filename = os.path.basename(filepath)
    data = []
    headers = {}
    boundary = '----------%d' % int(time.time())
    headers['content-type'] = 'multipart/form-data; boundary=%s' % boundary
    data.append(('--%s' % boundary).encode('utf-8'))
    data.append(('Content-Disposition: form-data; name="%s"; filename="%s"' % ('File1', filename)).encode('utf-8'))
    data.append(('Content-Type: %s' % get_content_type(filename)).encode('utf-8'))
    data.append(('').encode('utf-8'))
    temp = open(filepath, 'rb').read()
    data.append(temp)
    data.append(('--%s--' % boundary).encode('utf-8'))
    data.append(('').encode('utf-8'))
    data_str = newline.join(data)
    headers['content-length'] = len(data_str)
    
    uri = urlparse.urlparse(url)
    http = httplib.HTTPSConnection(uri.netloc)
    http.putrequest('POST', '%s?%s'%(uri.path, uri.query))
    for hdr_name, hdr_value in headers.items():
        http.putheader(hdr_name, hdr_value)
    http.endheaders()
    http.send(data_str)
    return http.getresponse()
    
def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    
#*******************************************************************************
# Parses given directory path and returns it as a string
# if get_parent_directory == 1, strip last item from given path
# if get_parent_directory == 0, return the entire given path
def parseDirectory(args, get_parent_directory):
    if(len(args.split('/')) > 1):
        argument_list = args.split('/')
    elif(len(args.split("\\")) > 1):
        argument_list = args.split("\\")
    
    directory_path = ""
    i=1
    
    for directory in argument_list:
        if(i==1):
            directory_path = directory
        elif(get_parent_directory==1 and i<len(argument_list)):
            directory_path += '/' + directory
        elif(get_parent_directory==0 and i<=len(argument_list)):
            directory_path += '/' + directory
        i+=1
    
    return directory_path

# Returns True if tasks exists (e.g. "StatusReady" is in the temp file created by createTaskCSV())    
def doesTaskExist(program_directory):
    createTaskCSV()
    program_directory += "/taskQuery.csv"
    # Read output from createTaskCSV() in taskQuery.csv
    with open(program_directory, 'r') as csvFile:
        csvReader = csv.reader(csvFile, delimiter=',')
        lineCount = 0
        output = ""
        targetString1 = "StatusRunning"
        targetString2 = "StatusReady"
        for row in csvReader:
            if lineCount <= 1:
                # 4th row contains status of the task
                output += row[3]
                if isMatch(targetString1, output):
                    return True
                elif isMatch(targetString2, output):
                    return True
                lineCount += 1
        return False

def isMatch(string1, string2):
    if (string1 is string2):
        return True
    else:
        return False

# Checks if task exists and stores output in temporary csv file
def createTaskCSV():
    taskCommand = "schtasks /query /fo CSV /v /TN \"ScreenGrab\ScreenGrab_Schedule\" >> \"" + program_directory + "/taskQuery.csv\""
    subprocess.call(taskCommand, shell=True)
    log.write("Task csv created")

def importTask():
    xml_path = parseDirectory(program_directory, 0) + "/ScreenGrab_Schedule.xml"
    taskCommand = "schtasks /Create /XML \"" + xml_path + "\" /TN \"\ScreenGrab\ScreenGrab_Schedule\""
    subprocess.call(taskCommand, shell=True)
    log.write("\nTask imported")

def removeFile(path):
    if os.path.isfile(path):
        os.remove(path)

def capture(localPath, screenId):
    # Capture/Save screenshot
    screenShot = pyautogui.screenshot()
    pathToScreenshot = parseDirectory(localPath, 0) + '/' + screenId + ".jpg"
    screenShot.save(pathToScreenshot)
    log.write("\nScreenshot captured and saved.")
    
    return pathToScreenshot

# program_directory contains the command sent by the task scheduler
# e.g. "C:/Users/user/Documents/ScreenGrab/ScreenGrab.exe"
program_directory = os.getcwd()
print("program_directory:")
print(program_directory)
ini_path = parseDirectory(program_directory, 0) + "/sharefile_conf.ini"
log_path = parseDirectory(program_directory, 0) + "/output_log.txt"

# Open log file and add current datetime + various paths
try:
    log = open(log_path, 'a')
    now = datetime.now()
    localtime = time.asctime(time.localtime(time.time()))
    log.write('\n\n\n' + localtime + '\n')
    log.write("\nprogram_directory: %s"%program_directory)
    log.write("\nini_path: %s"%ini_path)
    log.write("\nlog_path: %s"%log_path)
except IOError:
    print("Unable to open log file.\n")
    raise

# Read .ini file
config = configparser.ConfigParser()
try:
    config.read(ini_path)
except ConfigParser.NoSectionError:
    raise ValueError('Could not open ini file.')

# Initialize variables with .ini file contents
try:
    hostname = config.get('Sharefile API', 'hostname')
    username = config.get('Sharefile API', 'username')
    password = config.get('Sharefile API', 'password')
    client_id = config.get('Sharefile API', 'client_id')
    client_secret = config.get('Sharefile API', 'client_secret')
    screenId = config.get('SectionThree', 'screenId')
    localPath = config.get('SectionThree', 'localPath')
except configparser.NoSectionError:
    log.write("No Section Error")
    raise ValueError('The metadata value could not be determined.')

try:
    if __name__ == '__main__':   
        # Authenticate
        token = authenticate(hostname, client_id, client_secret, username, password)
    
        if token:
            # Take screenshot and save to 'localPath' with filename 'screenId'
            log.write("\nAuthentication successful")
            pathToScreenshot = capture(localPath, screenId)
            print("pathToScreenshot: " + pathToScreenshot)
            # Find folder in SF with name matching screenId
            rootFolder = get_root(token, 1)
            log.write("current file: ")
            for root in rootFolder:
                log.write(root['Name'])
                print("looking for file: " + screenId)
                if root['Name'] == screenId:
                    rootId = root['Id']
                else:
                    log.write("Wrong Root Id\n")
                
            # Upload file to ShareFile
            j = True
            while j==True and 'rootId' in locals():
                uploadResponse = upload_file(token, rootId, pathToScreenshot)
                
                if(uploadResponse == 200):
                    log.write("\nScreenshot successfully uploaded.")
                    j=False
                else:
                    log.write("\nUpload unsuccessful. Trying again..")
        
        # Check if screengrab scheduled task already exists. If not, import task.
            importTask()
            removeFile(program_directory + "/taskQuery.csv")
        else:
            log.write("\nAuthentication failed. No token")
except Exception as e:
    sys.exit()