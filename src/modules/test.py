import src.core.sql.users_sql as sql

user = sql.get_userid_by_name("lachlan_c_a")
username = sql.get_name_by_userid(6095551421)

print("USER ID: ", user[0].user_id)
print("USERNAME: ", username[0].username)