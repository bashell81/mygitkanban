# -*- coding: UTF-8 -*-
import os
import subprocess
import platform
import sys
import numpy as np
import matplotlib.pyplot as plt
import datetime
import webbrowser

#获取当前平台的操作系统类型
ON_LINUX = (platform.system() == 'Linux')

PATH_RESULT = 'C:/mygitkanban_result'

#根据指令集合返回结果，如果出现reading log message字样，可能是因为进入的目录不正确导致的阻塞
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
    return output.decode('utf-8').rstrip('\n') #此处是由于Python3返回字节集合需要通过转码变为字符串输出

#返回当前GIT工程提交代码的总人数
def getAuthorNumber():
    return int(getpipoutput(['git shortlog -s ', 'wc -l']))

#获取某日累计代码量
def getDailyLineNum(date=datetime.datetime.now().strftime('%Y-%m-%d')):
    daylinenum = getpipoutput(['git log  --pretty=tformat: --numstat --until=%s' % date, 'awk "{ add += $1; subs += $2; loc += $1 - $2 } END { printf  loc }" '])
    return str(daylinenum).split('\n')[0]

#返回开发者代码量
def getTotalLineNumByAuthor():
    #查找开发者
    output = getpipoutput(['git shortlog -s'])
    author_names = []
    author_lines = []
    for line in output.split('\n'):
        parts = line.split('\t')
        author_name = parts[1]
        author_names.append(author_name)
        authorline = getpipoutput(['git log  --pretty=tformat: --numstat  --author=%s' %author_name, 'awk "{ add += $1; subs += $2; loc += $1 - $2 } END { printf  loc }" '])
        #print(authorline+ "    "  + author_name)
        if not authorline or int(authorline) <= 0:
            authorline = 0
        author_lines.append(int(authorline))

    return author_names, author_lines

def pieComputer(pct, allvals):
    absolute = int(pct/100.*np.sum(allvals))
    return "{:.1f}%\n({:d})".format(pct, absolute)

def getResultPath():
    if os.path.exists(PATH_RESULT) == False:
        os.mkdir(PATH_RESULT)
    return PATH_RESULT

def makePieData(labels,datas,title='饼状图'):
    # plt.subplots定义画布和图型；figsize设置画布尺寸；aspect="equal"设置坐标轴的方正
    fig, ax = plt.subplots(figsize=(16, 8), subplot_kw=dict(aspect="equal"))

    wedges, texts, autotexts = ax.pie(datas, autopct=lambda pct: pieComputer(pct, datas), textprops=dict(color="w"))

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


    plt.savefig(getResultPath() + '/author_pie.png')
    plt.close()

def makeCubeImag(labels,datas,title='柱状图'):
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

    plt.savefig(getResultPath() + '/author_cube.png')
    plt.close()


def makeHTML(gitpaths):
    GEN_HTML = "/index.html"
    resultpath = getResultPath()
    f = open(getResultPath()+GEN_HTML, 'w')

    gitdata = GitDataCollector()

    str_showpath = ''
    for gitpath in gitpaths:
        print('Start Collecting : %s' % gitpath)
        os.chdir(gitpath)
        gitdata.collect(gitpath)
        str_showpath += gitpath + '<br>'


    print("开发者人数：" + str(gitdata.total_authors))
    print("代码总行数：" + str(gitdata.total_line))
    gitdata.drawPic()

    message = """
    <html>
    <head></head>
    <body>
    <p>统计代码工程如下:<br>%s</p>
    <p>开发者人数：%s</p>
    <p>代码总行数：%s</p>
    <p>代码分布饼图：<img src="author_pie.png"> </img></p>
    <p>代码分布柱状图：<img src="author_cube.png"> </img></p>
    </body>
    </html>""" % (str_showpath,gitdata.total_authors, gitdata.total_line)

    # 写入文件
    f.write(message)
    # 关闭文件
    f.close()

    # 运行完自动在网页中显示
    webbrowser.open(getResultPath()+GEN_HTML, new=1)

class GitDataCollector():
    def __init__(self):
        self.total_authors = 0
        self.total_line = 0
        self.authors = []
        self.authorlines = []

    def collect(self,dir):
        self.total_authors += int(getAuthorNumber())
        self.total_line += int(getDailyLineNum())

        tempauthors, tempauthorlines = getTotalLineNumByAuthor()
        for i,author in enumerate(tempauthors):
            if author not in self.authors:
                self.authors.append(author)
                self.authorlines.append(tempauthorlines[i])
            else:
                for j, a in enumerate(self.authors):
                    if author == self.authors[j]:
                        self.authorlines[j] += tempauthorlines[i]

    def drawPic(self):
        makePieData(self.authors, self.authorlines, '开发人员代码行数比例')
        makeCubeImag(self.authors,self.authorlines,'开发人员代码行数对比')

gitpaths = ['C:\eclipse4SpringCloud\lyfen-partner-platform',
                'C:\eclipse4SpringCloud_WorkSpace\yonyou-cloud-platform', 'C:\eclipse4SpringCloud_WorkSpace\lyfen',
                'C:\eclipse4SpringCloud_WorkSpace\zhongtai']
makeHTML(gitpaths)
