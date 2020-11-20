#! /usr/bin/env python3

import pymysql
import argparse

db_host = "qa-mysql-multisite-master-1.cnet.com"
db_user = "gcp_qa_read"
db_password = "GCPQaR3ad!"
db_db = "cmg_33"

db = pymysql.connect(db_host, db_user, db_password, db_db)
cursor = db.cursor()

action = "SELECT *"

def exec_sql(_sql, _what):
   #print("===> {0}...".format(_what))
   #print("Executing sql: {0}".format(_sql))

   try:
      cursor.execute(_sql)
   except:
      print("Error: unable to fetch data for {0}".format(_what))

def get_content_article_version_related_tables():
   sql = """
      SELECT 
      TABLE_NAME,COLUMN_NAME,CONSTRAINT_NAME, REFERENCED_TABLE_NAME,REFERENCED_COLUMN_NAME
      FROM
      INFORMATION_SCHEMA.KEY_COLUMN_USAGE
      WHERE
      REFERENCED_TABLE_SCHEMA = 'cmg_33' AND
      REFERENCED_TABLE_NAME = 'content_article_version' AND
      REFERENCED_COLUMN_NAME = 'id';
   """

   exec_sql(sql, 'get_content_article_version_related_tables')
   results = cursor.fetchall()

   _table_col_dict = {}

   for row in results:
      table = row[0]
      col = row[1]
      _table_col_dict[table] = col

   return _table_col_dict

def get_version_ids(_article_id):
   sql = """
      SELECT id FROM cmg_33.content_article_version
      WHERE id in (select new_version_id from cmg_33.content_version_activity_log where type_name = 'content_article' and content_id = '{0}' and date_event <= (CURDATE()-INTERVAL {1} DAY))
      AND id NOT in (select new_version_id from cmg_33.content_version_activity_log where type_name = 'content_article' and content_id = '{0}' and date_event > (CURDATE()-INTERVAL {1} DAY));
   """.format(_article_id, age)

   exec_sql(sql, 'get_version_ids')
   results = cursor.fetchall()

   _version_ids = set()
   for row in results:
      _version_ids.add(row[0])

   return _version_ids

def cleanup_content_article_version_related_tables(_table, _col, _version_id):
   sql = "select count(*) from {0} where {1} = '{2}'".format(_table, _col, _version_id)

   exec_sql(sql, "is_need_cleanup_content_article_version_related_tables")
   res = cursor.fetchone()

   cnt = res[0]
   if cnt > 0:
      clean_table_by_version(_table, _col, _version_id)

def clean_table_by_version(_table, _col, _version_id):
   print("\n     --> cleaning table [{0}] where {1} = '{2}'".format(_table, _col, _version_id))
   sql = "{0} from {1} where {2} = '{3}'".format(action, _table, _col, _version_id)
   exec_sql(sql, "clean_table {0}...".format(_table))
   res = cursor.fetchall()

   for row in res:
      print("\t{0}".format(row))

def clean_table_by_age(_table, _col, _article_id, _age):
   print("\n     --> cleaning table [{0}] where {1} = '{2}' by age of {3}".format(_table, _col, _article_id, age))

   if _table == 'content_version_activity_log':
      sql = "{0} FROM cmg_33.{1} WHERE type_name = 'content_article' and {2} = '{3}' and date_event <=  (CURDATE()-INTERVAL {4} DAY);".format(action, _table, _col, _article_id, _age)
   elif _table == 'content_activitylog':
      sql = "{0} FROM cmg_33.{1} WHERE object_type = 'content_article' and {2} = '{3}' and date_created <=  (CURDATE()-INTERVAL {4} DAY);".format(action, _table, _col, _article_id, _age)
   else:
      print("Not supported table [{0}]".format(_table))
      return

   exec_sql(sql, "clean_table {0}...".format(_table))
   res = cursor.fetchall()

   for row in res:
      print("\t{0}".format(row))


if __name__ == "__main__":

   ap = argparse.ArgumentParser()
   ap.add_argument("--article_id", help="flag to show KST code or not")
   ap.add_argument('--age', type=int, default=2, help="age to cleanup")
   ap.add_argument('--cleanup', default=False, action='store_true', help="flag to cleanup")
   args = vars(ap.parse_args())

   age = args['age']
   article_id = args['article_id']
   cleanup = args['cleanup']

   if cleanup:
      action = "DELETE"

   version_ids = get_version_ids(article_id)
   
   if version_ids:
      print("==> Cleaning article [{0}]...".format(article_id))
      table_col_dict = get_content_article_version_related_tables()

      for version_id in version_ids:
         print("\n   ==> Cleaning version# [{0}]...".format(version_id))
         for table in table_col_dict.keys():
            cleanup_content_article_version_related_tables(table, table_col_dict[table], version_id)
      
         # cleanup content_article_version
         clean_table_by_version('content_article_version', 'id', version_id)

      # cleanup content_version_activity_log
      clean_table_by_age('content_version_activity_log', 'content_id', article_id, age)
      # cleanup content_activitylog
      clean_table_by_age('content_activitylog', 'object_id', article_id, age)
   else:
      print("No cleanup needed for article [{0}]".format(article_id))

   db.close()
