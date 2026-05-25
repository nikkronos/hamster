from . import keys
from .work_db import *


async def get_data(table_name, select='*', fetch='one', **kwargs):
    '''Возвращает данные из таблицы БД'''
    query = '''
    SELECT
        {}
    FROM
        {}
    '''.format(
        select,
        table_name,
    )
    params, add_query = await get_params_for_query(**kwargs)
    query += add_query
    data = await execute_query(query, params, fetch=fetch)

    if not data:
        return

    if select != '*':
        if fetch == 'all':
            if ',' in select:
                return data
            else:
                return [i[0] for i in data]
        else:
            if ',' in select:
                return data
            else:
                return data[0]
    else:
        keys_table = list(keys.keys[table_name].keys())
        if fetch == 'all':
            return [dict(zip(keys_table, i)) for i in data]
        else:
            return dict(zip(keys_table, data))