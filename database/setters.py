import database
from . import keys
from .work_db import *


async def update_data(table_name, set, where):
    '''Обновление данных'''
    query = '''
    UPDATE
        {}
    SET
        {}
    WHERE
        {}
    '''.format(
        table_name,
        ', '.join([f'{i} = ?' for i in set]),
        ' AND '.join([f'{i} = ?' for i in where])
    )
    params = list(set.values()) + list(where.values())

    await execute_query(query, params)


async def add_new_data(
    table_name,
    data,
    keys=None,
    start_index=1,
    end_index="",
    many=False,
):
    """Добавление новых данных в таблицу БД"""
    if not keys:
        table_keys = list(database.keys.keys[table_name].keys())
    else:
        table_keys = keys

    if end_index:
        keys_for_query = table_keys[start_index:end_index]
    else:
        keys_for_query = table_keys[start_index:]

    query = '''
    INSERT INTO {}
        {}
    VALUES
        {};
    '''.format(
        table_name,
        "(" + ", ".join([key for key in keys_for_query]) + ")",
        "(" + ", ".join(["?" for _ in keys_for_query]) + ")",
    )

    return await execute_query(query, data, many=many)


async def delete_data(table_name, **kwargs):
    '''Удаление данных из таблицы'''
    query = '''
    DELETE
    FROM
        {}
    '''.format(table_name)
    params, add_query = await get_params_for_query(**kwargs)
    query += add_query

    await execute_query(query, params)