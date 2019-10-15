# -*- coding: UTF-8 -*-
import os
import subprocess
import platform
import sys
import numpy as np
import matplotlib.pyplot as plt
import datetime
import webbrowser
import collections
import configparser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import io

# 获取当前平台的操作系统类型
ON_LINUX = (platform.system() == 'Linux')
# 报告结果生成绝对路径
PATH_RESULT = 'C:/mygitkanban_result'
#代码趋势统计天数
config_code_trend_daynum = 20
#按开发者统计代码变化量到N周
config_code_perauthor_weeknum = 8
#统计往前N天的代码变化量
config_code_lastNdays = 10


# 根据指令集合返回结果，如果出现reading log message字样，可能是因为进入的目录不正确导致的阻塞
def getpipoutput(cmds, quiet=False):
    if not quiet and ON_LINUX and os.isatty(1):
        print
        '>> ' + ' | '.join(cmds),
        sys.stdout.flush()

    print(cmds)

    child = subprocess.Popen(cmds[0], stdout=subprocess.PIPE, shell=True)
    processes = [child]

    for x in cmds[1:]:
        child = subprocess.Popen(x, stdin=child.stdout, stdout=subprocess.PIPE, shell=True)
        processes.append(child)

    output = child.communicate()[0]

    for x in processes:
        x.wait()
    # 此处是由于Python3返回字节集合需要通过转码变为字符串输出
    return output.decode('utf-8').rstrip('\n')


# 获得生成结果页面的文件夹绝对路径，如果不存在则创建一个
def get_resultpath():
    if os.path.exists(PATH_RESULT) == False:
        os.mkdir(PATH_RESULT)
    return PATH_RESULT

# 返回当前GIT工程提交代码的总人数
def get_git_author_number():
    return int(getpipoutput(['git shortlog -s -- **/* ', 'wc -l']))

# 返回当前GIT工程对应的当前分支编码
def get_git_branch(dir):
    os.chdir(dir)
    blist = getpipoutput(['git branch'])
    for b in blist.split('\n'):
        if str(b).startswith('*'):
            return str(b)


# 遍历目录下所有文件，返回目录下git修改文件次数字典
def get_git_changetime_onefile(dir,topn=19):

    dict4change = collections.OrderedDict()
    for root, dirs, files in os.walk(dir):
        os.chdir(root)
        for file in files:
            abspath = root + '\\' + file
            if '.git' in abspath:
                continue
            num = getpipoutput(['git log --pretty=oneline %s ' %file,'wc -l'])

            dict4change[abspath] = int(num)
    d = list(zip(dict4change.values(), dict4change.keys()))
    d = sorted(d,reverse=True)

    retdict = collections.OrderedDict()
    # 返回Top 10
    for keyAndValue in d:
        retdict[keyAndValue[1]] = keyAndValue[0]
        if len(retdict) > topn:
            break

    return retdict

# 获取某日累计代码量
def get_git_linesum_until_somedate(date=datetime.datetime.now().strftime('%Y-%m-%d')):
    linesum = getpipoutput(['git log  --pretty=tformat: --numstat --until=%s -- **/*' % date, 'awk "{ add += $1; subs += $2; loc += $1 - $2 } END { printf  loc }" '])
    if not linesum:
        linesum = '0'
    return str(linesum).split('\n')[0]


# 获取某个开发者过去7天代码变动量
def get_git_linechange_last_ndays(author, ndays=6):
    now = datetime.date.today()
    ndaysago = (now - datetime.timedelta(days=ndays)).strftime('%Y-%m-%d')
    print('get_git_linechange_last_ndays author='+author)
    num = getpipoutput(['git log --pretty=tformat: --numstat --since=%s --author="%s" -- **/*' % (ndaysago,author), 'awk "{ add += $1; subs += $2; loc += $1 - $2 } END { print add;print subs;print loc }" '])

    numL = num.split('\n')
    if not num:
        numL = [0,0,0]

    num_list = {}

    if not numL[0]:
        num_list['add'] = 0
    else:
        num_list['add'] = int(numL[0])
    if not numL[1]:
        num_list['sub'] = 0
    else:
        num_list['sub'] = int(numL[1])
    if not numL[2]:
        num_list['loc'] = 0
    else:
        num_list['loc'] = int(numL[2])

    return num_list


# 获取过去N天的日期列表，按自然日期顺序返回
def getlastndays(ndays, date=datetime.datetime.now().strftime('%Y-%m-%d')):
    today = datetime.date.today()
    oneday= datetime.timedelta(days=1)
    lastdays = [today.strftime('%Y-%m-%d')]
    for n in range(1, ndays):
        today -= oneday
        lastdays.append(today.strftime('%Y-%m-%d'))
    lastdays.sort()

    return lastdays


# 获取过去N周的日期列表，按自然日排序
def getlastnweeks_begindate(nweek=5, currentday=datetime.datetime.now()):
    computday = currentday + datetime.timedelta(days=1)  #为了区间包含今天，先往后拨一天
    sevenday = datetime.timedelta(days=7)
    lastnweeks_begindate = []
    for n in range(nweek):
        computday -=sevenday
        lastnweeks_begindate.append(computday.strftime('%Y-%m-%d'))
    lastnweeks_begindate.sort()

    return lastnweeks_begindate


# 从git上获取过去N天的累计代码量
def get_git_linesum_perdays(ndays):
    lastdays = getlastndays(ndays)
    curr_line_nums = []
    for d in lastdays:
        curr_line_nums.append(get_git_linesum_until_somedate(d))
    return lastdays,curr_line_nums


#从git上获取过去N天每日变化代码行数
def get_git_linechange_perdays(inputdays):

    line_adds = []
    line_subs = []
    line_locs = []

    for d in inputdays:
        begintime = d+' 00:00:00'
        endtime = d+' 23:59:59'
        num = getpipoutput(['git log --pretty=tformat: --numstat --since="%s"  --until="%s"  -- **/* ' % (begintime, endtime),
                            'awk "{ add += $1; subs += $2; loc += $1 - $2 } END { print add;print subs;print loc }" '])
        numL = num.split('\n')
        if not num:
            numL = [0, 0, 0]
        num_list = {}
        if not numL[0]:
            num_list['add'] = 0
        else:
            num_list['add'] = int(numL[0])
        if not numL[1]:
            num_list['sub'] = 0
        else:
            num_list['sub'] = int(numL[1])
        if not numL[2]:
            num_list['loc'] = 0
        else:
            num_list['loc'] = int(numL[2])


        line_adds.append(num_list['add'])
        line_subs.append(num_list['sub'])
        line_locs.append(num_list['loc'])
        print(d +'当日代码变化+'+str(num_list['add']) + ' - '+ str(num_list['sub']))
    return line_adds, line_subs, line_locs


# 从git上获取某个开发者过去N周的代码变化量
def get_git_linesum_oneauthor_since_nweek(author_name,weekbegindates):
    linesum_oneauthor_since_nweek_add = []
    linesum_oneauthor_since_nweek_sub = []
    linesum_oneauthor_since_nweek_loc = []

    for sincedate in weekbegindates:
        untildate = datetime.datetime.strptime(sincedate, '%Y-%m-%d') + datetime.timedelta(days=6)
        #print("sincedate:" + sincedate + "untildate:" + untildate.strftime('%Y-%m-%d'))
        num = getpipoutput(['git log --pretty=tformat: --numstat --since=%s --until=%s --author="%s" -- **/*' % (sincedate, untildate.strftime('%Y-%m-%d'), author_name),
                            'awk "{ add += $1; subs += $2; loc += $1 - $2 } END { print add;print subs;print loc }" '])
        numL = num.split('\n')
        if not num:
            numL = [0, 0, 0]
        num_list = {}
        if not numL[0]:
            num_list['add'] = 0
        else:
            num_list['add'] = int(numL[0])
        if not numL[1]:
            num_list['sub'] = 0
        else:
            num_list['sub'] = int(numL[1])
        if not numL[2]:
            num_list['loc'] = 0
        else:
            num_list['loc'] = int(numL[2])

        linesum_oneauthor_since_nweek_add.append(num_list['add'])
        linesum_oneauthor_since_nweek_sub.append((num_list['sub']))
        linesum_oneauthor_since_nweek_loc.append((num_list['loc']))

    return linesum_oneauthor_since_nweek_add ,linesum_oneauthor_since_nweek_sub,linesum_oneauthor_since_nweek_loc

# 返回开发者代码量
def get_git_linesum_oneauthor(author_name):
    # 查找开发者，注意由于author名字可能有空格，所以要加双引号2019-09-04
    linesum = getpipoutput(['git log  --pretty=tformat: --numstat  --author="%s" -- **/* ' %author_name, 'awk "{ add += $1; subs += $2; loc += $1 - $2 } END { printf  loc }" '])
    if not linesum or int(linesum) <= 0:
        linesum = 0
    return int(linesum)


# 自动在当前路径下执行强制Merge更新到最新版本
def git_autogitpull():
    print('开始获取GIT最新代码...')
    print(getpipoutput(['git pull']))


# 查找工程下的开发者，重复的进行合并
def git_fundauthors(paths):
    author_names = []

    for path in paths:
        os.chdir(path)
        #查找开发者
        output = getpipoutput(['git log --pretty=format:"%ce" -- **/*'])
        for line in output.split('\n'):

            author_name = line
            if author_name not in author_names:
                author_names.append(author_name)

    return author_names


# 饼图标签显示内容设置
def img_annotation(pct, allvals):
    absolute = int(pct/100.*np.sum(allvals))
    return "{:.1f}%\n({:d})".format(pct, absolute)


# 按照输入数据饼图形式展示
def img_piedata(labels, datas, title='饼状图'):


    #如果只有一个人，则不生成饼图，控件似乎不支持
    if len(labels) == 1:
        pass

    # plt.subplots定义画布和图型；figsize设置画布尺寸；aspect="equal"设置坐标轴的方正
    fig, ax = plt.subplots(figsize=(16, 8), subplot_kw=dict(aspect="equal"))

    wedges, texts, autotexts = ax.pie(datas, autopct=lambda pct: img_annotation(pct, datas), textprops=dict(color="w"))

    ax.legend(wedges, labels,
              title="类别",
              loc="center left",
              bbox_to_anchor=(1, 0, 0.5, 1))
    plt.setp(autotexts, size=12, weight="bold")
    ax.set_title(title)
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
    bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=0.72)
    kw = dict(arrowprops=dict(arrowstyle="-"),
              bbox=bbox_props, zorder=0, va="center")

    for i, p in enumerate(wedges):
        ang = (p.theta2 - p.theta1) / 2. + p.theta1
        y = np.sin(np.deg2rad(ang))
        x = np.cos(np.deg2rad(ang))
        horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
        connectionstyle = "angle,angleA=0,angleB={}".format(ang)
        kw["arrowprops"].update({"connectionstyle": connectionstyle})
        ax.annotate(labels[i], xy=(x, y), xytext=(1.35 * np.sign(x), 1.4 * y),
                    horizontalalignment=horizontalalignment, **kw)
    try:
        plt.savefig(get_resultpath() + '/author_pie.png')
    except BaseException as e:
        print(e)

    plt.close()


# 根据输入数据形成柱状图
def img_cubedata_horizontal(labels, datas, title='柱状图'):

    plt.rcdefaults()
    fig, ax = plt.subplots(figsize=(16, 8))
    y_pos = np.arange(len(labels))

    ax.barh(y_pos, datas, align='center')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel('开发者')
    ax.set_title(title)
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
    plt.savefig(get_resultpath() + '/author_cube.png')
    plt.close()


# 根据数据形成代码趋势
def img_ploylinedata(labels, datas, title='代码趋势图'):
    fig, ax = plt.subplots(figsize=(20, 10))
    ax.plot(labels, datas)
    ax.grid(True, linestyle='-.')
    ax.tick_params(labelcolor='r', labelsize='medium', width=3)
    ax.set_title(title)

    for a, b in zip(labels, datas):
        plt.text(a, b, b, ha='center', va='bottom', fontsize=20)

    plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
    plt.savefig(get_resultpath() + '/daily_line.png')
    plt.close()


# 根据数据形成最近7天代码变化柱状图
def img_cubedata_3bar(labels, values1, values2, values3, filename ,filterzero=False,xlabel='开发者', ylabel='代码量', title="最近7日代码变化" ):
    if filterzero :
        labels, values1, values2, values3 = filterzerodata4Three(labels, values1, values2, values3)
    if not labels:
        return

    fig, ax = plt.subplots(figsize=(16, 8))
    n_groups = len(labels)
    index = np.arange(n_groups)

    bar_width = 0.2
    opacity = 0.4

    rects1 = ax.bar(index, values1, bar_width,
                    alpha=opacity, color='b',
                    label='新增')
    rects2 = ax.bar(index+ bar_width, values2, bar_width,
                    alpha=opacity, color='m',
                    label='删除')
    rects3 = ax.bar(index+ bar_width+ bar_width, values3, bar_width,
                    alpha=opacity, color='r',
                    label='合计')
    ax.set_xticks(index + 3 * bar_width / 3)
    ax.set_xticklabels(labels)
    ax.legend()
    ax.set_title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
    plt.savefig(get_resultpath() + '/'+filename+'.png')
    plt.close()


# 生成结果报告
def gen_reporthtml(gitpaths,pull=True):
    GEN_HTML = "/index.html"
    f = open(get_resultpath() + GEN_HTML, 'w', encoding='gb18030')

    gitdata = GitDataCollector(gitpaths)
    gitdata.collect_all(pull)
    gitdata.drawimg()

    #根据开发者动态生成每个开发者近5周画像
    showpath = ''

    showMaxChangeFileAll = ''
    for p in gitdata.gitpaths:

        title = '<p>工程路径:'+p +'</p>'
        showMaxChangeFile = title +'<table><tr><td>文件路径</td><td>提交次数Top20</td></tr>'
        showpath += p
        showpath += '   当前统计分支为：'+get_git_branch(p) + '<br>'
        changedict = get_git_changetime_onefile(p)
        for key,value in changedict.items():
            showMaxChangeFile += '<tr><td>'+str(key)+'</td><td>'+str(value)+'</td></tr>'
        showMaxChangeFile = showMaxChangeFile + '</table>'
        showMaxChangeFileAll += showMaxChangeFile

    every_author_message = ''

    for au in gitdata.authors:
        every_author_message +='<p><img src="'+au+'_weekchange.png"/><img src="cid:'+au+'_weekchange.png"/></p>'

    message = """
    <html>
    <meta http-equiv="Content-Type" content="text/html; charset=gbk" />
    <head></head>
    <body>
    <p>统计代码工程如下:<br>%s</p>
    <p>开发者人数：%s</p>
    <p>代码总行数：%s</p>
    <p>最近每日代码变化情况:<img src="cid:lastnday_change.png"/><img src="lastnday_change.png"/></p>
    <p>最近开发者代码变化：<img src="cid:daily_change_line.png"/><img src="daily_change_line.png"/>  </p>
    %s
    <p>代码分布饼图：<img src="cid:author_pie.png"/><img src="author_pie.png"/>  </p>
    <p>代码分布柱状图：<img src="cid:author_cube.png"/><img src="author_cube.png"/>  </p>
    <p>代码日趋势：<img src="cid:daily_line.png"/><img src="daily_line.png"/>  </p>
    <p>文件更新(TOP20建议做代码分析)：%s</p>
    </body>
    </html>""" % (showpath, gitdata.total_authornum, gitdata.total_line, every_author_message,showMaxChangeFileAll)

    # 改变标准输出的默认编码
    # utf-8中文乱码
    #sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='gb18030')

    # 写入文件
    f.write(message)
    # 关闭文件
    f.close()

    # 运行完自动在网页中显示
    webbrowser.open(get_resultpath() + GEN_HTML, new=1)


#去掉值全为0的开发者
def filterdata4One(keys,values):
    r_keys = []
    r_values = []
    for i , key in enumerate(keys):
        if  values[i] == 0:
            pass
        else:
            r_keys.append(key)
            r_values.append(values[i])
    return r_keys,r_values


#去掉值全为0的开发者
def filterdata4Two(keys,values1,values2):
    r_keys = []
    r_values1 = []
    r_values2 = []
    for i,key in enumerate(keys):
        if  values1[i]== 0 and values2[i]== 0:
            pass
        else:
            r_keys.append(key)
            r_values1.append(values1[i])
            r_values2.append(values2[i])
    return r_keys, r_values1, r_values2


#去掉值全为0的开发者
def filterzerodata4Three(keys,values1,values2,values3):
    r_keys = []
    r_values1 = []
    r_values2 = []
    r_values3 = []
    for i,key in enumerate(keys):
        if values1[i]==0 and values2[i]==0 and values3[i]==0:
            pass
        else:
            r_keys.append(key)
            r_values1.append(values1[i])
            r_values2.append(values2[i])
            r_values3.append(values3[i])
    return r_keys,r_values1,r_values2,r_values3


# git工程数据收集器
class GitDataCollector():
    def __init__(self, paths):
        # git工程合计代码行数
        self.total_line = 0
        # 过去N天日期
        self.last14days = getlastndays(config_code_trend_daynum)
        # 过去N周每日代码量
        self.last14days_num = [0 for x in range(config_code_trend_daynum)]
        self.gitpaths = paths
        # git工程开发者编码集合
        self.authors = git_fundauthors(paths)

        # git工程开发者合计数
        self.total_authornum = len(self.authors)
        # 过去七天增减
        self.author_adds_last7days = [0 for x in range(len(self.authors))]
        self.author_subs_last7days = [0 for x in range(len(self.authors))]
        self.author_loc_last7days =  [0 for x in range(len(self.authors))]
        # git工程开发者代码行数，顺序与开发者编码一致
        self.authorlines = [0 for x in range(self.total_authornum)]

        # 往前N周起始日期组
        self.lastnweeks_begindates = getlastnweeks_begindate(nweek=config_code_perauthor_weeknum)

        self.oneauthor_lastweeks_linesums_add = {}
        self.oneauthor_lastweeks_linesums_sub = {}
        self.oneauthor_lastweeks_linesums_loc = {}

        for au in self.authors:
            self.oneauthor_lastweeks_linesums_add[au] = [0 for x in range(config_code_perauthor_weeknum)]
            self.oneauthor_lastweeks_linesums_sub[au] = [0 for x in range(config_code_perauthor_weeknum)]
            self.oneauthor_lastweeks_linesums_loc[au] = [0 for x in range(config_code_perauthor_weeknum)]

        #最近N天每日代码变更量
        self.lastNdays = getlastndays(config_code_lastNdays)


        self.lastNdays_linenum_add = [0 for x in range(config_code_lastNdays)]
        self.lastNdays_linenum_del = [0 for x in range(config_code_lastNdays)]
        self.lastNdays_linenum_loc = [0 for x in range(config_code_lastNdays)]


    # 收集git数据
    def collect_all(self, pullcode=True):
        for gitpath in self.gitpaths:
            print('Start Collecting : %s' % gitpath)
            os.chdir(gitpath)
            if pullcode:
                git_autogitpull()
            self.collect(gitpath)




    #  数据收集
    def collect(self, dir):

        temp_adds, temp_subs, temp_locs = get_git_linechange_perdays(self.lastNdays)
        for i in range(config_code_lastNdays):

            self.lastNdays_linenum_add[i] += temp_adds[i]
            self.lastNdays_linenum_del[i] += temp_subs[i]
            self.lastNdays_linenum_loc[i] += temp_locs[i]



        self.total_line += int(get_git_linesum_until_somedate())

        for i, au in enumerate(self.authors):
            self.authorlines[i] += get_git_linesum_oneauthor(au)
            num_list = get_git_linechange_last_ndays(au)
            self.author_adds_last7days[i] += num_list['add']
            self.author_subs_last7days[i] += num_list['sub']
            self.author_loc_last7days[i] += num_list['loc']

            linesum_oneauthor_since_nweek_add,linesum_oneauthor_since_nweek_sub,linesum_oneauthor_since_nweek_loc = get_git_linesum_oneauthor_since_nweek(au,self.lastnweeks_begindates)
            for x in range(config_code_perauthor_weeknum):
                self.oneauthor_lastweeks_linesums_add[au][x] += linesum_oneauthor_since_nweek_add[x]
                self.oneauthor_lastweeks_linesums_sub[au][x] += linesum_oneauthor_since_nweek_sub[x]
                self.oneauthor_lastweeks_linesums_loc[au][x] += linesum_oneauthor_since_nweek_loc[x]


        for i in range(config_code_trend_daynum):
            self.last14days_num[i] += int(get_git_linesum_until_somedate(self.last14days[i]))





    # 形成图表
    def drawimg(self):
        namelabels = readchinese(self.authors)
        img_piedata(namelabels, self.authorlines, '开发人员代码行数比例')
        img_cubedata_horizontal(namelabels, self.authorlines, '开发人员代码行数对比')
        img_ploylinedata(self.last14days, self.last14days_num, 'GIT工程代码趋势图')
        img_cubedata_3bar(labels=namelabels,
                          values1=self.author_adds_last7days,
                          values2=self.author_subs_last7days,
                          values3=self.author_loc_last7days,
                          filterzero = True,
                          filename='daily_change_line')
        for au,name in zip(self.authors,namelabels):
            img_cubedata_3bar(labels=self.lastnweeks_begindates,
                              values1=self.oneauthor_lastweeks_linesums_add[au],
                              values2=self.oneauthor_lastweeks_linesums_sub[au],
                              values3=self.oneauthor_lastweeks_linesums_loc[au],
                              filename=au+'_weekchange',
                              title=name +'最近周代码变动量')

        img_cubedata_3bar(labels=self.lastNdays,
                          values1=self.lastNdays_linenum_add,
                          values2=self.lastNdays_linenum_del,
                          values3=self.lastNdays_linenum_loc,
                          filename='lastnday_change',
                          title='最近7天代码每日变动情况')


def sendmsg(subject,receivers,attfolder):
    mail_host = "mail.yonyou.com"  # 设置服务器
    mail_user = "xwq"  # 用户名
    mail_pass = "001226"  # 口令



    # 创建一个带附件的实例
    message = MIMEMultipart()
    #message['From'] = Header("用友上海分公司GIT代码看板", 'utf-8')
    #message['To'] = Header("测试", 'utf-8')

    message['Subject'] = Header(subject, 'utf-8')

    txt_html = open(attfolder+"\\index.html", "r").read()

    message.attach(MIMEText(txt_html, 'html', 'utf-8'))
    message["Accept-Language"]="zh-CN"
    message["Accept-Charset"]="ISO-8859-1,utf-8"
    sender = 'xwq@yonyou.com'

    for parent, dirnames, filenames in os.walk(attfolder, followlinks=True):
        for filename in filenames:
            file_path = os.path.join(parent, filename)
            if os.path.split(file_path)[-1] != 'index.html':
                att = MIMEText(open(file_path, 'rb').read(), 'base64', 'utf-8')
                att["Content-Type"] = 'application/octet-stream'
                att["Content-Disposition"] = 'attachment; filename="'+os.path.split(file_path)[-1]+'"'
                att['Content-ID'] = os.path.split(file_path)[-1]
                message.attach(att)
    try:
        smtpObj = smtplib.SMTP()
        smtpObj.connect(mail_host, 25)  # 25 为 SMTP 端口号
        smtpObj.login(mail_user, mail_pass)
        smtpObj.sendmail(sender, receivers, message.as_string())
        print("邮件发送成功")
    except smtplib.SMTPException:
        print("Error: 无法发送邮件")


# 读取邮箱对应的中文名
def readchinese(emails):
    labels = []
    for e in emails:
        labels.append(namedict[e])
    return labels

def getnamedict(infile):
    input_file = open(infile, mode="r", encoding="utf-8")
    infile_content = input_file.readlines()
    namedict = {}
    for each in infile_content:
        s = each.split('=')
        print(s)
        namedict[str(s[0])] = s[1]

    print(namedict)
    input_file.close()
    return namedict

# 获取文件的当前路径（绝对路径）
cur_path = os.path.dirname(os.path.realpath(__file__))

# 读取中文名配置
try:
    namedict = getnamedict(cur_path+'\\usernames.ini')
except BaseException as e:
        print(e)


configfile = sys.argv[1]
print("配置文件" + configfile)
# 获取config.ini的路径
config_path = os.path.join(cur_path, configfile)
conf = configparser.ConfigParser()
conf.read(config_path,encoding='utf-8')

gitpaths = conf.get('path', 'GIT_PATHS').split(',')

p = conf.get('path', 'UPDATE_CODE')
PATH_RESULT = conf.get('path', 'PATH_RESULT')

gen_reporthtml(gitpaths,True if p.upper()=='Y' else False)
try:
    MAIL_TO = conf.get('path','MAIL_TO').split(';')
    MAIL_TITLE = conf.get('path','MAIL_TITLE')
    print(MAIL_TITLE)
    title = '用友上海分公司GIT代码看板'
    if  MAIL_TITLE :
        title = MAIL_TITLE
    sendmsg(title, MAIL_TO, PATH_RESULT)
except BaseException as e:
        print(e)



