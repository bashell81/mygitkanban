# -*- coding: UTF-8 -*-
import os
import subprocess
import platform
import sys
import numpy as np
import matplotlib.pyplot as plt
import datetime
import webbrowser

# 获取当前平台的操作系统类型
ON_LINUX = (platform.system() == 'Linux')
# 报告结果生成绝对路径
PATH_RESULT = 'C:/mygitkanban_result'


# 根据指令集合返回结果，如果出现reading log message字样，可能是因为进入的目录不正确导致的阻塞
def getpipoutput(cmds, quiet=False):
    if not quiet and ON_LINUX and os.isatty(1):
        print
        '>> ' + ' | '.join(cmds),
        sys.stdout.flush()

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
    return int(getpipoutput(['git shortlog -s ', 'wc -l']))


# 获取某日累计代码量
def get_git_linesum_until_somedate(date=datetime.datetime.now().strftime('%Y-%m-%d')):
    linesum = getpipoutput(['git log  --pretty=tformat: --numstat --until=%s' % date, 'awk "{ add += $1; subs += $2; loc += $1 - $2 } END { printf  loc }" '])
    if not linesum:
        linesum = '0'
    return str(linesum).split('\n')[0]


# 获取某个开发者过去7天代码变动量
def get_git_linechange_last_ndays(author, ndays=7):
    now = datetime.date.today()
    ndaysago = (now - datetime.timedelta(days=ndays)).strftime('%Y-%m-%d')
    num = getpipoutput(['git log --pretty=tformat: --numstat --since=%s --author=%s' % (ndaysago,author), 'awk "{ add += $1; subs += $2; loc += $1 - $2 } END { print add;print subs;print loc }" '])

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


# 从git上获取过去N天的累计代码量
def get_git_linesum_perdays(ndays):
    lastdays = getlastndays(ndays)
    curr_line_nums = []
    for d in lastdays:
        curr_line_nums.append(get_git_linesum_until_somedate(d))
    return lastdays,curr_line_nums


# 返回开发者代码量
def get_git_linesum_oneauthor(author_name):
    # 查找开发者
    linesum = getpipoutput(['git log  --pretty=tformat: --numstat  --author=%s' %author_name, 'awk "{ add += $1; subs += $2; loc += $1 - $2 } END { printf  loc }" '])
    if not linesum or int(linesum) <= 0:
        linesum = 0
    return int(linesum)


# 饼图标签显示内容设置
def img_annotation(pct, allvals):
    absolute = int(pct/100.*np.sum(allvals))
    return "{:.1f}%\n({:d})".format(pct, absolute)


# 按照输入数据饼图形式展示
def img_piedata(labels, datas, title='饼状图'):
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

    plt.savefig(get_resultpath() + '/author_pie.png')
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
    fig, ax = plt.subplots(figsize=(16, 8))
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
def img_cubedata_3bar(labels, values1, values2, values3, xlabel='开发者', ylabel='代码量', title="最近7日代码变化"):
    fig, ax = plt.subplots(figsize=(16, 8))
    n_groups = len(labels)
    index = np.arange(n_groups)

    bar_width = 0.2
    opacity = 0.4
    print(values1)
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
    plt.savefig(get_resultpath() + '/daily_change_line.png')
    plt.close()


# 生成结果报告
def gen_reporthtml(gitpaths, updatecode=True):
    GEN_HTML = "/index.html"
    resultpath = get_resultpath()
    f = open(get_resultpath() + GEN_HTML, 'w')
    gitdata = GitDataCollector()
    gitdata.initMeta(gitpaths)

    for gitpath in gitpaths:
        print('Start Collecting : %s' % gitpath)
        os.chdir(gitpath)
        if updatecode:
            autogitpull()
        gitdata.collect(gitpath)

    gitdata.drawimg()

    message = """
    <html>
    <head></head>
    <body>
    <p>统计代码工程如下:<br>%s</p>
    <p>开发者人数：%s</p>
    <p>代码总行数：%s</p>
    <p>最近7日代码变化：<img src="daily_change_line.png"> </img></p>
    <p>代码分布饼图：<img src="author_pie.png"> </img></p>
    <p>代码分布柱状图：<img src="author_cube.png"> </img></p>
    <p>代码日趋势：<img src="daily_line.png"> </img></p>
    </body>
    </html>""" % (gitdata.gitpaths, gitdata.total_authornum, gitdata.total_line)

    # 写入文件
    f.write(message)
    # 关闭文件
    f.close()

    # 运行完自动在网页中显示
    webbrowser.open(get_resultpath() + GEN_HTML, new=1)


# 自动在当前路径下执行强制Merge更新到最新版本
def autogitpull():
    print(getpipoutput(['git pull']))


# 查找工程下的开发者，重复的进行合并
def git_fundauthors(paths):
    author_names = []

    for path in paths:
        os.chdir(path)
        #查找开发者
        output = getpipoutput(['git shortlog -s'])
        for line in output.split('\n'):
            parts = line.split('\t')
            author_name = parts[1]
            if author_name not in author_names:
                author_names.append(author_name)

    return author_names


# git工程数据收集器
class GitDataCollector():
    def __init__(self):
        # git工程开发者合计数
        self.total_authornum = 0
        # git工程合计代码行数
        self.total_line = 0
        # git工程开发者编码集合
        self.authors = []
        # git工程开发者代码行数，顺序与开发者编码一致
        self.authorlines = []
        self.last14days = getlastndays(14)
        # 过去2周每日代码量
        self.last14days_num = [0 for x in range(14)]

        # 过去七天增减,按照200开发人员来初始化
        self.author_adds_last7days = []
        self.author_subs_last7days = []
        self.author_loc_last7days = []
        self.gitpaths = []

    def initMeta(self, paths):
        self.gitpaths = paths
        self.authors = git_fundauthors(paths)
        self.total_authornum = len(self.authors)
        self.author_adds_last7days = [0 for x in range(len(self.authors))]
        self.author_subs_last7days = [0 for x in range(len(self.authors))]
        self.author_loc_last7days =  [0 for x in range(len(self.authors))]
        self.authorlines = [0 for x in range(self.total_authornum)]

    # 数据收集
    def collect(self,dir):
        self.total_line += int(get_git_linesum_until_somedate())

        for i, au in enumerate(self.authors):
            self.authorlines[i] += get_git_linesum_oneauthor(au)
            num_list = get_git_linechange_last_ndays(au)
            self.author_adds_last7days[i] += num_list['add']
            self.author_subs_last7days[i] += num_list['sub']
            self.author_loc_last7days[i] += num_list['loc']

        for i in range(14):
            self.last14days_num[i] += int(get_git_linesum_until_somedate(self.last14days[i]))

    # 形成图表
    def drawimg(self):
        img_piedata(self.authors, self.authorlines, '开发人员代码行数比例')
        img_cubedata_horizontal(self.authors, self.authorlines, '开发人员代码行数对比')
        img_ploylinedata(self.last14days, self.last14days_num, 'GIT工程代码趋势图')
        img_cubedata_3bar(labels=self.authors, values1=self.author_adds_last7days, values2=self.author_subs_last7days, values3=self.author_loc_last7days)


gitpaths = ['C:\eclipse4SpringCloud\lyfen-partner-platform',
            'C:\eclipse4SpringCloud_WorkSpace\yonyou-cloud-platform',
            'C:\eclipse4SpringCloud_WorkSpace\lyfen',
            'C:\eclipse4SpringCloud_WorkSpace\zhongtai']

gen_reporthtml(gitpaths, False)

