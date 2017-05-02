# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

from urllib import unquote
from falcon import HTTPError, HTTP_201, HTTPBadRequest
from ujson import dumps as json_dumps
from ... import db
from .users import get_user_data
from ...auth import login_required, check_team_auth
from ...utils import load_json_body, subscribe_notifications, create_audit
from ...constants import ADMIN_CREATED


def on_get(req, resp, team):
    """
    Get list of admin users for a team
    """
    team = unquote(team)
    connection = db.connect()
    cursor = connection.cursor()
    cursor.execute('''SELECT `user`.`name` FROM `user`
                      JOIN `team_admin` ON `team_admin`.`user_id`=`user`.`id`
                      JOIN `team` ON `team`.`id`=`team_admin`.`team_id`
                      WHERE `team`.`name`=%s''',
                   team)
    data = [r[0] for r in cursor]
    cursor.close()
    connection.close()
    resp.body = json_dumps(data)


@login_required
def on_post(req, resp, team):
    """
    Add user as team admin
    """
    team = unquote(team)
    check_team_auth(team, req)
    data = load_json_body(req)

    user_name = data.get('name')
    if not user_name:
        raise HTTPBadRequest('name attribute missing from request')

    connection = db.connect()
    cursor = connection.cursor()

    cursor.execute('''(SELECT `id` FROM `team` WHERE `name`=%s)
                      UNION
                      (SELECT `id` FROM `user` WHERE `name`=%s)''', (team, user_name))
    results = [r[0] for r in cursor]
    if len(results) < 2:
        raise HTTPError('422 Unprocessable Entity', 'IntegrityError', 'invalid team or user')
    (team_id, user_id) = results

    try:
        # also make sure user is in the team
        cursor.execute('''INSERT IGNORE INTO `team_user` (`team_id`, `user_id`) VALUES (%r, %r)''',
                       (team_id, user_id))
        cursor.execute('''INSERT INTO `team_admin` (`team_id`, `user_id`) VALUES (%r, %r)''',
                       (team_id, user_id))
        # subscribe user to team notifications
        subscribe_notifications(team, user_name, cursor)
        create_audit({'user': user_name}, team, ADMIN_CREATED, req, cursor)
        connection.commit()
    except db.IntegrityError as e:
        err_msg = str(e.args[1])
        if err_msg == "Column 'team_id' cannot be null":
            err_msg = 'team %s not found' % team
        if err_msg == "Column 'user_id' cannot be null":
            err_msg = 'user %s not found' % data['name']
        else:
            err_msg = 'user name "%s" is already an admin of team %s' % (data['name'], team)
        raise HTTPError('422 Unprocessable Entity', 'IntegrityError', err_msg)
    finally:
        cursor.close()
        connection.close()

    resp.status = HTTP_201
    resp.body = json_dumps(get_user_data(None, {'name': user_name})[0])
