import json
import httplib
import os
import mimetypes
import time
import urlparse
import urllib

import ConfigParser

import MySQLdb
import glob
#############################################
def authenticate(hostname, client_id, client_secret, username, password):
    uri_path = '/oauth/token'
    headers = {'Content-Type':'application/x-www-form-urlencoded'}
    params = {'grant_type':'password', 'client_id':client_id, 'client_secret':client_secret,
              'username':username, 'password':password}
    http = httplib.HTTPSConnection(hostname)
    http.request('POST', uri_path, urllib.urlencode(params), headers=headers)
    response = http.getresponse()
    print response.status, response.reason
    token = None
    if response.status == 200:
        token = json.loads(response.read())
        print 'Received token info', token
    http.close()
    return token

def get_hostname(token):
    return '%s.sf-api.com'%(token['subdomain'])
def get_authorization_header(token):
    return {'Authorization':'Bearer %s'%(token['access_token'])}
def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'
def multipart_form_post_upload(url, filepath):
    newline = '\r\n'
    filename = os.path.basename(filepath)
    data = []
    headers = {}
    boundary = '----------%d' % int(time.time())
    headers['content-type'] = 'multipart/form-data; boundary=%s' % boundary
    data.append('--%s' % boundary)
    data.append('Content-Disposition: form-data; name="%s"; filename="%s"' % ('File1', filename))
    data.append('Content-Type: %s' % get_content_type(filename))
    data.append('')
    data.append(open(filepath, 'rb').read())
    data.append('--%s--' % boundary)
    data.append('')
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

def get_root(token, get_children=False):
    """ Get the root level Item for the provided user. To retrieve Children the $expand=Children
    parameter can be added.

    Args:
    dict json token acquired from authenticate function
    boolean get_children - retrieve Children Items if True, default is False"""

    uri_path = '/sf/v3/Items(allshared)'
    if get_children:
        uri_path = '%s?$expand=Children'%(uri_path)
    print 'GET %s%s'%(get_hostname(token), uri_path)
    http = httplib.HTTPSConnection(get_hostname(token))
    http.request('GET', uri_path, headers=get_authorization_header(token))
    response = http.getresponse()

    print response.status, response.reason
    items = json.loads(response.read())
    print items['Id'], items['CreationDate'], items['Name']
    print "here"
    if 'Children' in items:
        children = items['Children']
        for child in children:
            print "here"
            print child['Id'], items['CreationDate'], child['Name']
    return child['Id']

def upload_file(token, folder_id, local_path):
    uri_path = '/sf/v3/Items(%s)/Upload'%(folder_id)
    print 'GET %s%s'%(get_hostname(token), uri_path)
    http = httplib.HTTPSConnection(get_hostname(token))
    http.request('GET', uri_path, headers=get_authorization_header(token))

    response = http.getresponse()
    upload_config = json.loads(response.read())
    if 'ChunkUri' in upload_config:
        upload_response = multipart_form_post_upload(upload_config['ChunkUri'], local_path)
        print upload_response.status, upload_response.reason
    else:
        print 'No Upload URL received'
    return upload_response.status
#########################################



config = ConfigParser.ConfigParser()
config.read('./myconf.ini')

login = config.get('SectionOne', 'user')
passwd = config.get('SectionOne', 'pass')
localPath = config.get('SectionOne', 'localPath')
hostname = config.get('Sharefile API', 'hostname')
username = config.get('Sharefile API', 'username')
password = config.get('Sharefile API', 'password')
client_id = config.get('Sharefile API', 'client_id')
client_secret = config.get('Sharefile API', 'client_secret')



if __name__ == '__main__':
    token = authenticate(hostname, client_id, client_secret, username, password)
    if token:
        root_Id = get_root(token, password)
	#empty folder that will hold screenshots
	files = glob.glob(localPath + '*')
	for f in files:
		os.remove(f)
	#construsct ffmpeg command
	ffmpeg1 = "sudo ffmpeg -rtsp_transport tcp -i "
	ffmpeg2 = " -ss 00:00:5 -vframes 1 -vf scale=640:-1 " + localPath
	#loop through database to get screenshot of each known camera stream
	db = MySQLdb.connect(host="localhost", user=login, passwd=passwd, db="Website")
	cur = db.cursor()
	cur.execute("SELECT * FROM Cameras, RTSP_Streams Where RTSP_Streams.id = Cameras.ID AND RTSP_Streams.Resolution = 'high'")
	for row in cur.fetchall() :
		url = str(row[5])
	        filename = "'" + str(row[1]) + ".png'"
		uploadFile = localPath + str(row[1]) + '.png'
	        screengrab = ffmpeg1 + url + ffmpeg2 + filename
		os.system(screengrab)
		uploadResponse = upload_file(token, root_Id , uploadFile)
		if (uploadResponse == 200):
	        	print("Uploaded file")
	        else:
	        	print("Error uploading file!")
