import sqlite3

from database import keys

DB_PATH = 'database/database.sqlite'


async def get_connect(db_name=DB_PATH):
    '''Возвращает подключение к БД'''
    return sqlite3.connect(db_name)


async def get_params_for_query(**kwargs):
    '''Возвращает список параметров для запроса'''
    if kwargs:
        params = list(kwargs.values())
        query = ' WHERE ' + ' AND '.join([f'{i} = ?' for i in kwargs])
    else:
        params = []
        query = ''

    return params, query


async def execute_query(query, params=None, fetch=False, db_name=DB_PATH, 
                        many=False):
    '''Отправляет запрос к БД'''
    connect = await get_connect(db_name)
    cursor = connect.cursor()
    
    if many:
        cursor.executemany(query, params)
    else:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

    if fetch == 'one':
        return cursor.fetchone()
    elif fetch == 'all':
        return cursor.fetchall()

    connect.commit()
    connect.close()
    
    return cursor.lastrowid


async def create_tables():
    '''Создание таблиц в БД'''
    for table_name, field_data in keys.keys.items():
        field_for_query = []

        for name, type_field in field_data.items():
            name = name.replace(' ', '_').replace('(', '').replace(')', '')
            field_for_query.append(f'{name} {type_field}')

        field_for_query = ',\n'.join(field_for_query)
        query = '''
        CREATE TABLE IF NOT EXISTS {} (
            {}
        );
        '''.format(table_name, field_for_query)

        await execute_query(query)