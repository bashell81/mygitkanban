import pymysql
import datetime


# DB information
DB_HOST = '123.56.118.102'
DB_PORT = 3306
DB_USER = 'kk_kanban'
DB_PASSWORD = 'Hong2008+!'
DB_DATABASE = 'kk_kanban'

# 更新项目代码更新情况表
def insertProjectUpdateInfo(remoteurl,addline,delline,locline,users):
    conn=pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_DATABASE,
        charset='utf8'
    )
    cursor = conn.cursor()
    t = datetime.datetime.now()

    # 当前日期
    now = t.strftime('%Y-%m-%d %H:%M:%S')
    #先查询看是否已存在该项目，没有就新增，有就更新
    qry_cmd = "select * from PROJECT_CODEUPDATE where remoteurl='%s'" % remoteurl
    ret = cursor.execute(qry_cmd)
    if ret == 0:
        mysql_cmd = "INSERT INTO PROJECT_CODEUPDATE(remoteurl,addline,delline,locline,users,ts)values('%s',%s,%s,%s,'%s')"%(remoteurl,addline,delline,locline,users,now)
    else:
        mysql_cmd = "UPDATE PROJECT_CODEUPDATE SET addline=%s,delline=%s,locline=%s,ts='%s',users ='%s' WHERE remoteurl='%s'" % (addline,delline,locline,now,users,remoteurl)
    cursor.execute(mysql_cmd)

    conn.commit()
    cursor.close()  # 关闭游标
    conn.close()  # 关闭连接


