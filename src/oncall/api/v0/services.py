# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from falcon import HTTPError, HTTP_201
from ujson import dumps as json_dumps

from ... import db
from ...utils import load_json_body
from ...auth import debug_only

constraints = {
    'id': '`service`.`id` = %s',
    'id__eq': '`service`.`id` = %s',
    'id__ne': '`service`.`id` != %s',
    'id__lt': '`service`.`id` < %s',
    'id__le': '`service`.`id` <= %s',
    'id__gt': '`service`.`id` > %s',
    'id__ge': '`service`.`id` >= %s',
    'name': '`service`.`name` = %s',
    'name__eq': '`service`.`name` = %s',
    'name__contains': '`service`.`name` LIKE CONCAT("%%", %s, "%%")',
    'name__startswith': '`service`.`name` LIKE CONCAT(%s, "%%")',
    'name__endswith': '`service`.`name` LIKE CONCAT("%%", %s)'
}


def on_get(req, resp):
    """
    Search for services
    """
    query = 'SELECT `name` FROM `service`'

    where_params = []
    where_vals = []
    for key in req.params:
        val = req.get_param(key)
        if key in constraints:
            where_params.append(constraints[key])
            where_vals.append(val)
    where_query = ' AND '.join(where_params)

    if where_query:
        query = '%s WHERE %s' % (query, where_query)

    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute(query, where_vals)
    data = [r[0] for r in cursor]
    cursor.close()
    connection.close()
    resp.body = json_dumps(data)


@debug_only
def on_post(req, resp):
    data = load_json_body(req)

    connection = db.connect()
    cursor = connection.cursor()
    try:
        cursor.execute('INSERT INTO `service` (`name`) VALUES (%(name)s)', data)
        connection.commit()
    except db.IntegrityError:
        raise HTTPError('422 Unprocessable Entity',
                        'IntegrityError',
                        'service name "%(name)s" already exists' % data)
    finally:
        cursor.close()
        connection.close()

    resp.status = HTTP_201
