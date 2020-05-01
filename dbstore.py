import pymysql
import datetime


# DB information
DB_HOST = '123.56.118.102'
DB_PORT = 3306
DB_USER = 'kk_kanban'
DB_PASSWORD = 'Hong2008+!'
DB_DATABASE = 'kk_kanban'

# 更新项目代码更新情况表
def insertProjectUpdateInfo(remoteurl,addline,delline,locline,users,curbranch,ndays=30):
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

    tablename = 'PROJECT_CODEUPDATE'
    if ndays == 7:
        tablename = 'PROJECT_CODEUPDATE7'

    # 当前日期
    now = t.strftime('%Y-%m-%d %H:%M:%S')
    #先查询看是否当天已存在该项目，没有就新增，有就更新
    qry_cmd = "select * from %s where remoteurl='%s' and TO_DAYS(ts)=TO_DAYS(now()) and curbranch='%s'" % (tablename,remoteurl,curbranch)
    ret = cursor.execute(qry_cmd)
    if ret == 0:
        mysql_cmd = "INSERT INTO %s(remoteurl,addline,delline,locline,users,ts,curbranch)values('%s',%s,%s,%s,'%s','%s','%s')"%(tablename,remoteurl,addline,delline,locline,users,now,curbranch)

    else:
        mysql_cmd = "UPDATE %s SET addline=%s,delline=%s,locline=%s,ts='%s',users ='%s' WHERE remoteurl='%s' and TO_DAYS(ts)=TO_DAYS(now())  and curbranch ='%s'" % (tablename,addline,delline,locline,now,users,remoteurl,curbranch)

    print(mysql_cmd)
    cursor.execute(mysql_cmd)

    conn.commit()
    cursor.close()  # 关闭游标
    conn.close()  # 关闭连接

