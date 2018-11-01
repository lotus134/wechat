
import re
import time
import json
import requests
from django.shortcuts import render
from django.shortcuts import HttpResponse
# 当前时间戳
CURRENT_TIME = None
QCODE = None

LOGIN_COOKIE_DICT = {}
TICKET_COOKIE_DICT = {}
TICKET_DICT = {}
TIPS = 1

USER_INIT_DATA = {}
BASE_URL = "http://wx.qq.com"
BASE_SYNC_URL = "https://webpush.weixin.qq.com"

def login(request):
    base_qcode_url = 'https://login.wx.qq.com/jslogin?appid=wx782c26e4c19acffb&redirect_uri=https%3A%2F%2Fwx.qq.com%2Fcgi-bin%2Fmmwebwx-bin%2Fwebwxnewloginpage&fun=new&lang=zh_CN&_={0}'
    global CURRENT_TIME
    CURRENT_TIME = str(time.time())
    q_code_url = base_qcode_url.format(CURRENT_TIME)
    response = requests.get(q_code_url)
    # 二维码后缀
    code = re.findall('uuid = "(.*)";',response.text)[0]
    global QCODE
    QCODE = code
    return render(request, 'login.html', {'code': code})

def long_polling(request):
    print('polling....')
    ret = {'status': 408, 'data': None}
    # https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid=IZpsHyzTNw==&tip=1&r=-897465901&_=1486956149964
    # 408，201，200
    try:
        global TIPS
        base_login_url = 'https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid={0}&tip={1}&r=-897465901&_={2}'
        login_url = base_login_url.format(QCODE,TIPS,CURRENT_TIME)
        response_login = requests.get(login_url)
        if "window.code=201" in response_login.text:
            TIPS = 0
            avatar = re.findall("userAvatar = '(.*)';",response_login.text)[0]
            ret['data'] = avatar
            ret['status'] = 201
        elif 'window.code=200' in response_login.text:
            # 扫码点击确认后，获取cookie
            LOGIN_COOKIE_DICT.update(response_login.cookies.get_dict())
            redirect_uri = re.findall('redirect_uri="(.*)";', response_login.text)[0]
            global BASE_URL
            global BASE_SYNC_URL
            if redirect_uri.startswith('https://wx2.qq.com'):
                BASE_URL = 'https://wx2.qq.com'
                BASE_SYNC_URL = 'https://webpush.wx2.qq.com'
            else:
                BASE_URL = "http://wx.qq.com"
                BASE_SYNC_URL = "https://webpush.weixin.qq.com"

            redirect_uri += '&fun=new&version=v2&lang=zh_CN'

            # 获取票据，Cookie,返回值
            response_ticket = requests.get(redirect_uri, cookies=LOGIN_COOKIE_DICT)
            TICKET_COOKIE_DICT.update(response_ticket.cookies.get_dict())
            print(response_ticket.text)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response_ticket.text,'html.parser')
            for tag in soup.find():
                TICKET_DICT[tag.name] = tag.string

            ret['status'] = 200

            # https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage?ticket=AZfYKn7CWTeZE_iMTHwv7GFB@qrticket_0&uuid=IeFZHVi6Jw==&lang=zh_CN&scan=1
            # https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage?ticket=AepqqS0wvk1UN6bCGiaHHWXQ@qrticket_0&uuid=we1gq4TyyA==&lang=zh_CN&scan=1486957549"
    except Exception as e:
        print(e)
    return HttpResponse(json.dumps(ret))


def index(request):
    # 初始化用户基本信息
    # https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=-909239606&lang=zh_CN&pass_ticket=Tpc2XEec%252BJ0q2qNRw6nqWzGSsQ3jM2LZtBCVJZfjvMTDxjiyJ9mO5eRtCNOveeXO


    user_init_url = '%s/cgi-bin/mmwebwx-bin/webwxinit?pass_ticket=%s&r=%s' % (BASE_URL, TICKET_DICT['pass_ticket'], int(time.time()))

    form_data = {
        'BaseRequest': {
            'DeviceID': 'e531777446530354',
            'Sid': TICKET_DICT['wxsid'],
            'Skey': TICKET_DICT['skey'],
            'Uin': TICKET_DICT['wxuin']
        }
    }
    all_cookie_dict = {}
    all_cookie_dict.update(LOGIN_COOKIE_DICT)
    all_cookie_dict.update(TICKET_COOKIE_DICT)

    response_init = requests.post(user_init_url, json=form_data, cookies=all_cookie_dict)
    response_init.encoding = 'utf-8'
    user_init_data = json.loads(response_init.text)
    # for k,v in user_init_data.items():
    #     print(k,v)
    USER_INIT_DATA.update(user_init_data)
    """
    form_data = {
        'BaseRequest':{
        'DeviceID': 'e531777446530354',
        'Sid': TICKET_DICT['wxsid'],
        'Skey': TICKET_DICT['skey'],
        'Uin': TICKET_DICT['wxuin']
        }
    }
    all_cookie_dict = {}
    all_cookie_dict.update(LOGIN_COOKIE_DICT)
    all_cookie_dict.update(TICKET_COOKIE_DICT)

    response_init = requests.post(user_init_url,json=form_data,)
    response_init.encoding = 'utf-8'
    print(response_init.text)
    """

    return render(request, 'index.html',{'data': user_init_data})


def contact_list(request):
    """
    获取联系人列表
    :param request:
    :return:
    """
    # https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?lang=zh_CN&pass_ticket={0}&r={1}&seq=0&skey={2}
    base_url  = "{0}/cgi-bin/mmwebwx-bin/webwxgetcontact?lang=zh_CN&pass_ticket={1}&r={2}&seq=0&skey={3}"
    url = base_url.format(BASE_URL, TICKET_DICT['pass_ticket'], str(time.time()), TICKET_DICT['skey'])

    all_cookie_dict = {}
    all_cookie_dict.update(LOGIN_COOKIE_DICT)
    all_cookie_dict.update(TICKET_COOKIE_DICT)
    response = requests.get(url,cookies=all_cookie_dict)
    response.encoding = 'utf-8'
    contact_list_dict = json.loads(response.text)
    return render(request, 'contact_list.html',{'obj': contact_list_dict})


def send_msg(request):

    from_user_id = USER_INIT_DATA['User']['UserName']
    to_user_id = request.POST.get('user_id')
    msg = request.POST.get('user_msg')

    send_url = BASE_URL + "/cgi-bin/mmwebwx-bin/webwxsendmsg?lang=zh_CN&pass_ticket=" + TICKET_DICT['pass_ticket']
    form_data = {
        'BaseRequest': {
            'DeviceID': 'e531777446530354',
            'Sid': TICKET_DICT['wxsid'],
            'Skey': TICKET_DICT['skey'],
            'Uin': TICKET_DICT['wxuin']
        },
        'Msg':{
            "ClientMsgId": str(time.time()),
            "Content": '%(content)s',
            "FromUserName": from_user_id,
            "LocalID": str(time.time()),
            "ToUserName": to_user_id,
            "Type": 1
        },
        'Scene':0
    }
    import json
    # 字符串
    form_data_str = json.dumps(form_data)
    # 进行格式化
    form_data_str = form_data_str %{'content':msg}

    # 转换成字节
    form_data_bytes = bytes(form_data_str,encoding='utf-8')

    all_cookie_dict = {}
    all_cookie_dict.update(LOGIN_COOKIE_DICT)
    all_cookie_dict.update(TICKET_COOKIE_DICT)

    response = requests.post(send_url, data=form_data_bytes, cookies=all_cookie_dict, headers={
        'Content-Type': 'application/json'})
    print(response.text)

    return HttpResponse('ok')

def get_msg(request):
    sync_url = BASE_SYNC_URL + "/cgi-bin/mmwebwx-bin/synccheck"

    sync_data_list = []
    for item in USER_INIT_DATA['SyncKey']['List']:
        temp = "%s_%s" % (item['Key'], item['Val'])
        sync_data_list.append(temp)
    sync_data_str = "|".join(sync_data_list)
    nid = int(time.time())
    sync_dict = {
        "r": nid,
        "skey": TICKET_DICT['skey'],
        "sid": TICKET_DICT['wxsid'],
        "uin": TICKET_DICT['wxuin'],
        "deviceid": "e531777446530354",
        "synckey": sync_data_str
    }
    all_cookie = {}
    all_cookie.update(LOGIN_COOKIE_DICT)
    all_cookie.update(TICKET_COOKIE_DICT)
    response_sync = requests.get(sync_url, params=sync_dict, cookies=all_cookie)
    print(response_sync.text)
    if 'selector:"2"' in response_sync.text:
        fetch_msg_url = "%s/cgi-bin/mmwebwx-bin/webwxsync?sid=%s&skey=%s&lang=zh_CN&pass_ticket=%s" % (BASE_URL, TICKET_DICT['wxsid'], TICKET_DICT['skey'], TICKET_DICT['pass_ticket'])

        form_data = {
            'BaseRequest': {
                'DeviceID': 'e531777446530354',
                'Sid': TICKET_DICT['wxsid'],
                'Skey': TICKET_DICT['skey'],
                'Uin': TICKET_DICT['wxuin']
            },
            'SyncKey': USER_INIT_DATA['SyncKey'],
            'rr': str(time.time())
        }
        response_fetch_msg = requests.post(fetch_msg_url, json=form_data)
        response_fetch_msg.encoding = 'utf-8'
        res_fetch_msg_dict = json.loads(response_fetch_msg.text)
        USER_INIT_DATA['SyncKey'] = res_fetch_msg_dict['SyncKey']
        for item in res_fetch_msg_dict['AddMsgList']:
            print(item['Content'], ":::::", item['FromUserName'], "---->", item['ToUserName'], )
    return HttpResponse('ok')