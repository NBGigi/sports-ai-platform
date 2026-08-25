from database.connection import get_connection
from database.queries import insert_team


connection = get_connection()

insert_team(connection, 33, "Manchester United")
insert_team(connection, 36, "Fulham")

connection.close()

print("Teams inserted successfully")