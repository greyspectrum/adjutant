# Copyright (C) 2015 Catalyst IT Ltd
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json

from datetime import timedelta

from unittest import skip

from django.utils import timezone
from django.core import mail

import mock

from rest_framework import status
from rest_framework.test import APITestCase

from adjutant.api.models import Task, Token, Notification
from adjutant.api.v1.tests import (FakeManager, setup_temp_cache,
                                   modify_dict_settings)


@mock.patch('adjutant.actions.user_store.IdentityManager',
            FakeManager)
class AdminAPITests(APITestCase):
    """
    Tests to ensure the admin api endpoints work as expected within
    the context of the approval/token workflow.
    """

    def test_no_token_get(self):
        """
        Should be a 404.
        """
        url = "/v1/tokens/e8b3f57f5da64bf3a6bf4f9bbd3a40b5"
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.json(),
            {'errors': ['This token does not exist or has expired.']})

    def test_no_token_post(self):
        """
        Should be a 404.
        """
        url = "/v1/tokens/e8b3f57f5da64bf3a6bf4f9bbd3a40b5"
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.json(),
            {'errors': ['This token does not exist or has expired.']})

    def test_task_get(self):
        """
        Test the basic task detail view.
        """
        setup_temp_cache({}, {})

        url = "/v1/actions/CreateProject"
        data = {'project_name': "test_project", 'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        new_task = Task.objects.all()[0]
        url = "/v1/tasks/" + new_task.uuid
        response = self.client.get(url, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_no_task_get(self):
        """
        Should be a 404.
        """
        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        url = "/v1/tasks/e8b3f57f5da64bf3a6bf4f9bbd3a40b5"
        response = self.client.get(url, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.json(), {'errors': ['No task with this id.']})

    def test_no_task_post(self):
        """
        Should be a 404.
        """
        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        url = "/v1/tasks/e8b3f57f5da64bf3a6bf4f9bbd3a40b5"
        response = self.client.post(url, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.json(), {'errors': ['No task with this id.']})

    def test_token_expired_post(self):
        """
        Expired token should do nothing, then delete itself.
        """

        user = mock.Mock()
        user.id = 'user_id'
        user.name = "test@example.com"
        user.email = "test@example.com"
        user.domain = 'default'
        user.password = "test_password"

        setup_temp_cache({}, {user.id: user})

        url = "/v1/actions/ResetPassword"
        data = {'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()['notes'],
            ['If user with email exists, reset token will be issued.'])

        new_token = Token.objects.all()[0]
        new_token.expires = timezone.now() - timedelta(hours=24)
        new_token.save()
        url = "/v1/tokens/" + new_token.token
        data = {'password': 'new_test_password'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.json(),
            {'errors': ['This token does not exist or has expired.']})
        self.assertEqual(0, Token.objects.count())

    def test_token_expired_get(self):
        """
        Expired token should do nothing, then delete itself.
        """

        user = mock.Mock()
        user.id = 'user_id'
        user.name = "test@example.com"
        user.email = "test@example.com"
        user.domain = 'default'
        user.password = "test_password"

        setup_temp_cache({}, {user.id: user})

        url = "/v1/actions/ResetPassword"
        data = {'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()['notes'],
            ['If user with email exists, reset token will be issued.'])

        new_token = Token.objects.all()[0]
        new_token.expires = timezone.now() - timedelta(hours=24)
        new_token.save()
        url = "/v1/tokens/" + new_token.token
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.json(),
            {'errors': ['This token does not exist or has expired.']})
        self.assertEqual(0, Token.objects.count())

    def test_token_get(self):
        """
        Token should contain actions, task_type, required fields.
        """

        user = mock.Mock()
        user.id = 'user_id'
        user.name = "test@example.com"
        user.email = "test@example.com"
        user.domain = 'default'
        user.password = "test_password"

        setup_temp_cache({}, {user.id: user})

        url = "/v1/actions/ResetPassword"
        data = {'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()['notes'],
            ['If user with email exists, reset token will be issued.'])

        new_token = Token.objects.all()[0]
        url = "/v1/tokens/" + new_token.token
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {u'actions': [u'ResetUserPasswordAction'],
             u'required_fields': [u'password'],
             u'task_type': 'reset_password'})
        self.assertEqual(1, Token.objects.count())

    def test_token_list_get(self):
        user = mock.Mock()
        user.id = 'user_id'
        user.name = "test@example.com"
        user.email = "test@example.com"
        user.domain = 'default'
        user.password = "test_password"

        setup_temp_cache({}, {user.id: user})

        url = "/v1/actions/ResetPassword"
        data = {'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['notes'],
            ['If user with email exists, reset token will be issued.'])

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        first_task_id = Task.objects.all()[0].uuid

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        url = "/v1/tokens/"

        response = self.client.get(url, headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.json()['tokens']), 2)
        self.assertEqual(response.json()['tokens'][1]['task'],
                         first_task_id)

    def test_task_complete(self):
        """
        Can't approve a completed task.
        """
        setup_temp_cache({}, {})

        url = "/v1/actions/CreateProject"
        data = {'project_name': "test_project", 'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        new_task = Task.objects.all()[0]
        new_task.completed = True
        new_task.save()
        url = "/v1/tasks/" + new_task.uuid
        response = self.client.post(url, {'approved': True}, format='json',
                                    headers=headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {'errors': ['This task has already been completed.']})

    def test_status_page(self):
        """
        Status page gives details of last_created_task, last_completed_task
        and error notifcations
        """

        setup_temp_cache({}, {})

        url = "/v1/actions/CreateProject"
        data = {'project_name': "test_project", 'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        url = "/v1/status/"
        response = self.client.get(url, headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['last_created_task'][
            'actions'][0]['data']['email'], 'test@example.com')
        self.assertEqual(response.json()['last_completed_task'], None)

        self.assertEqual(response.json()['error_notifications'], [])

        # Create a second task and ensure it is the new last_created_task
        url = "/v1/actions/CreateProject"
        data = {'project_name': "test_project_2",
                'email': "test_2@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        url = "/v1/status/"
        response = self.client.get(url, headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['last_created_task'][
            'actions'][0]['data']['email'], 'test_2@example.com')
        self.assertEqual(response.json()['last_completed_task'], None)

        self.assertEqual(response.json()['error_notifications'], [])

        new_task = Task.objects.all()[0]
        new_task.completed = True
        new_task.save()

        url = "/v1/status/"
        response = self.client.get(url, headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['last_completed_task'][
            'actions'][0]['data']['email'], 'test@example.com')
        self.assertEqual(response.json()['last_created_task'][
            'actions'][0]['data']['email'], 'test_2@example.com')

        self.assertEqual(response.json()['error_notifications'], [])

    def test_task_update(self):
        """
        Creates a invalid task.

        Updates it and attempts to reapprove.
        """

        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        setup_temp_cache({'test_project': project}, {})

        url = "/v1/actions/CreateProject"
        data = {'project_name': "test_project", 'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }

        new_task = Task.objects.all()[0]
        url = "/v1/tasks/" + new_task.uuid
        response = self.client.post(url, {'approved': True}, format='json',
                                    headers=headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = {
            'project_name': "test_project2",
            'email': "test@example.com",
            'region': 'RegionOne',
        }
        response = self.client.put(url, data, format='json',
                                   headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {'notes': ['Task successfully updated.']})

        response = self.client.post(url, {'approved': True}, format='json',
                                    headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {'notes': ['created token']})

    def test_notification_get(self):
        """
        Test that you can get details of an induvidual notfication.
        """
        setup_temp_cache({}, {})

        url = "/v1/actions/CreateProject"
        data = {'project_name': "test_project", 'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        new_task = Task.objects.all()[0]

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        note = Notification.objects.first().uuid

        url = "/v1/notifications/%s" % note
        response = self.client.get(url, headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()['task'],
            new_task.uuid)
        self.assertEqual(
            response.json()['notes'],
            {u'notes': [u'New task for CreateProject.']})
        self.assertEqual(
            response.json()['error'], False)

    def test_notification_doesnt_exist(self):
        """
        Test that you get a 404 trying to access a non-existent notification.
        """
        setup_temp_cache({}, {})

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        note = "notarealnotifiactionuuid"

        url = "/v1/notifications/%s/" % note
        response = self.client.get(url, headers=headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(),
                         {"errors": ["No notification with this id."]})

    def test_notification_acknowledge(self):
        """
        Test that you can acknowledge a notification.
        """
        setup_temp_cache({}, {})

        url = "/v1/actions/CreateProject"
        data = {'project_name': "test_project", 'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        new_task = Task.objects.all()[0]

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }

        url = "/v1/notifications"
        response = self.client.get(url, headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["notifications"][0]['task'],
            new_task.uuid)

        url = ("/v1/notifications/%s/" %
               response.json()["notifications"][0]['uuid'])
        data = {'acknowledged': True}
        response = self.client.post(url, data, format='json', headers=headers)
        self.assertEqual(response.json(),
                         {'notes': ['Notification acknowledged.']})

        url = "/v1/notifications"
        params = {
            "filters": json.dumps({
                "acknowledged": {"exact": False}
            })
        }
        response = self.client.get(
            url, params, format='json', headers=headers
        )
        self.assertEqual(response.json(), {'notifications': []})

    def test_notification_acknowledge_doesnt_exist(self):
        """
        Test that you cant acknowledge a non-existent notification.
        """
        setup_temp_cache({}, {})

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }

        url = "/v1/notifications/dasdaaaiooiiobksd/"
        response = self.client.post(url, headers=headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(),
                         {'errors':
                         ['No notification with this id.']})

    def test_notification_re_acknowledge(self):
        """
        Test that you cant reacknowledge a notification.
        """
        setup_temp_cache({}, {})

        url = "/v1/actions/CreateProject"
        data = {'project_name': "test_project", 'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }

        note_id = Notification.objects.first().uuid
        url = "/v1/notifications/%s/" % note_id
        data = {'acknowledged': True}
        response = self.client.post(url, data, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(),
                         {'notes': ['Notification acknowledged.']})

        response = self.client.post(url, data, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(),
                         {'notes': ['Notification already acknowledged.']})

    def test_notification_acknowledge_no_data(self):
        """
        Test that you have to include 'acknowledged': True to the request.
        """
        setup_temp_cache({}, {})

        url = "/v1/actions/CreateProject"
        data = {'project_name': "test_project", 'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }

        note_id = Notification.objects.first().uuid
        url = "/v1/notifications/%s/" % note_id
        data = {}
        response = self.client.post(url, data, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(),
                         {u'acknowledged': [u'this field is required.']})

    def test_notification_acknowledge_list(self):
        """
        Test that you can acknowledge a list of notifications.
        """
        setup_temp_cache({}, {})

        url = "/v1/actions/CreateProject"
        data = {'project_name': "test_project", 'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = {'project_name': "test_project2", 'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }

        url = "/v1/notifications"
        response = self.client.get(url, headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        url = "/v1/notifications"
        notifications = response.json()["notifications"]
        data = {'notifications': [note['uuid'] for note in notifications]}
        response = self.client.post(url, data, format='json', headers=headers)
        self.assertEqual(response.json(),
                         {'notes': ['Notifications acknowledged.']})

        url = "/v1/notifications"
        params = {
            "filters": json.dumps({
                "acknowledged": {"exact": False}
            })
        }
        response = self.client.get(
            url, params, format='json', headers=headers
        )
        self.assertEqual(response.json(), {'notifications': []})

    def test_notification_acknowledge_list_empty_list(self):
        """
        Test that you cannot acknowledge an empty list of notifications.
        """
        setup_temp_cache({}, {})

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }

        url = "/v1/notifications"
        response = self.client.get(url, headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = {'notifications': []}
        response = self.client.post(url, data, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(),
                         {u'notifications':
                          [u'this field is required and needs to be a list.']})

    @modify_dict_settings(DEFAULT_TASK_SETTINGS={
        'key_list': ['notifications'],
        'operation': 'override',
        'value': {
            'EmailNotification': {
                'standard': {
                    'emails': ['example@example.com'],
                    'reply': 'no-reply@example.com',
                    'template': 'notification.txt'
                },
                'error': {
                    'emails': ['example@example.com'],
                    'reply': 'no-reply@example.com',
                    'template': 'notification.txt'
                }
            }
        }
    }, TASK_SETTINGS={
        'key_list': ['create_project', 'emails'],
        'operation': 'override',
        'value': {
            'initial': None,
            'token': None,
            'completed': None
        }
    })
    def test_notification_email(self):
        """
        Tests the email notification engine
        """
        setup_temp_cache({}, {})

        url = "/v1/actions/CreateProject"
        data = {'project_name': "test_project", 'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        new_task = Task.objects.all()[0]

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }

        url = "/v1/notifications"
        response = self.client.get(url, headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["notifications"][0]['task'],
            new_task.uuid)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'create_project notification')
        self.assertTrue("New task for CreateProject" in mail.outbox[0].body)

    def test_token_expired_delete(self):
        """
        test deleting of expired tokens.
        """

        user = mock.Mock()
        user.id = 'user_id'
        user.name = "test@example.com"
        user.email = "test@example.com"
        user.domain = 'default'
        user.password = "test_password"

        user2 = mock.Mock()
        user2.id = 'user_id2'
        user2.name = "test2@example.com"
        user2.email = "test2@example.com"
        user2.domain = 'default'
        user2.password = "test_password"

        setup_temp_cache({}, {user.id: user, user2.name: user2})

        url = "/v1/actions/ResetPassword"
        data = {'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()['notes'],
            ['If user with email exists, reset token will be issued.'])

        url = "/v1/actions/ResetPassword"
        data = {'email': "test2@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()['notes'],
            ['If user with email exists, reset token will be issued.'])

        tokens = Token.objects.all()

        self.assertEqual(len(tokens), 2)

        new_token = tokens[0]
        new_token.expires = timezone.now() - timedelta(hours=24)
        new_token.save()

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        url = "/v1/tokens/"
        response = self.client.delete(url, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(),
                         {'notes': ['Deleted all expired tokens.']})
        self.assertEqual(Token.objects.count(), 1)

    def test_token_reissue(self):
        """
        test for reissue of tokens
        """

        user = mock.Mock()
        user.id = 'user_id'
        user.name = "test@example.com"
        user.email = "test@example.com"
        user.domain = 'default'
        user.password = "test_password"

        setup_temp_cache({}, {user.id: user})

        url = "/v1/actions/ResetPassword"
        data = {'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()['notes'],
            ['If user with email exists, reset token will be issued.'])

        task = Task.objects.all()[0]
        new_token = Token.objects.all()[0]

        uuid = new_token.token

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        url = "/v1/tokens/"
        data = {"task": task.uuid}
        response = self.client.post(url, data, format='json',
                                    headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(),
                         {'notes': ['Token reissued.']})
        self.assertEqual(Token.objects.count(), 1)
        new_token = Token.objects.all()[0]
        self.assertNotEquals(new_token.token, uuid)

    def test_token_reissue_non_admin(self):
        """
        test for reissue of tokens for non-admin
        """

        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        setup_temp_cache({'test_project': project}, {})

        url = "/v1/actions/InviteUser"
        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "project_admin,_member_,project_mod",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        data = {'email': "test@example.com", 'roles': ["_member_"],
                'project_id': 'test_project_id'}
        response = self.client.post(url, data, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'notes': ['created token']})

        task = Task.objects.all()[0]
        new_token = Token.objects.all()[0]

        uuid = new_token.token

        url = "/v1/tokens/"
        data = {"task": task.uuid}
        response = self.client.post(url, data, format='json',
                                    headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(),
                         {'notes': ['Token reissued.']})
        self.assertEqual(Token.objects.count(), 1)
        new_token = Token.objects.all()[0]
        self.assertNotEquals(new_token.token, uuid)

        # Now confirm it is limited by project id properly.
        headers['project_id'] = "test_project_id2"
        response = self.client.post(url, data, format='json',
                                    headers=headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(),
                         {'errors': ['No task with this id.']})

    def test_token_reissue_task_cancelled(self):
        """
        Tests that a cancelled task cannot have a token reissued
        """

        user = mock.Mock()
        user.id = 'user_id'
        user.name = "test@example.com"
        user.email = "test@example.com"
        user.domain = 'default'
        user.password = "test_password"

        setup_temp_cache({}, {user.id: user})

        url = "/v1/actions/ResetPassword"
        data = {'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()['notes'],
            ['If user with email exists, reset token will be issued.'])

        task = Task.objects.all()[0]
        task.cancelled = True
        task.save()
        self.assertEqual(Token.objects.count(), 1)

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        url = "/v1/tokens/"
        data = {"task": task.uuid}
        response = self.client.post(url, data, format='json',
                                    headers=headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(),
                         {'errors': ['This task has been cancelled.']})

    def test_token_reissue_task_completed(self):
        """
        Tests that a completed task cannot have a token reissued
        """

        user = mock.Mock()
        user.id = 'user_id'
        user.name = "test@example.com"
        user.email = "test@example.com"
        user.domain = 'default'
        user.password = "test_password"

        setup_temp_cache({}, {user.id: user})

        url = "/v1/actions/ResetPassword"
        data = {'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()['notes'],
            ['If user with email exists, reset token will be issued.'])

        task = Task.objects.all()[0]
        task.completed = True
        task.save()
        self.assertEqual(Token.objects.count(), 1)

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        url = "/v1/tokens/"
        data = {"task": task.uuid}
        response = self.client.post(url, data, format='json',
                                    headers=headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(),
                         {'errors': ['This task has already been completed.']})

    def test_token_reissue_task_not_approve(self):
        """
        Tests that an unapproved task cannot have a token reissued
        """

        setup_temp_cache({}, {})

        url = "/v1/actions/CreateProject"
        data = {'email': "test@example.com", "project_name": "test_project"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()['notes'], [u'task created'])

        task = Task.objects.all()[0]

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        url = "/v1/tokens/"
        data = {"task": task.uuid}
        response = self.client.post(url, data, format='json',
                                    headers=headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(),
                         {'errors': ['This task has not been approved.']})

    def test_cancel_task(self):
        """
        Ensure the ability to cancel a task.
        """

        setup_temp_cache({}, {})

        url = "/v1/actions/CreateProject"
        data = {'project_name': "test_project", 'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        new_task = Task.objects.all()[0]
        url = "/v1/tasks/" + new_task.uuid
        response = self.client.delete(url, format='json',
                                      headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(url, {'approved': True}, format='json',
                                    headers=headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.put(url, format='json',
                                   headers=headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_task_sent_token(self):
        """
        Ensure the ability to cancel a task after the token is sent.
        """

        setup_temp_cache({}, {})

        url = "/v1/actions/CreateProject"
        data = {'project_name': "test_project", 'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        new_task = Task.objects.all()[0]
        url = "/v1/tasks/" + new_task.uuid
        response = self.client.post(url, {'approved': True}, format='json',
                                    headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.delete(url, format='json',
                                      headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        new_token = Token.objects.all()[0]
        url = "/v1/tokens/" + new_token.token
        data = {'password': 'testpassword'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reapprove_task_delete_tokens(self):
        """
        Tests that a reapproved task will delete all of it's previous tokens.
        """

        setup_temp_cache({}, {})

        url = "/v1/actions/CreateProject"
        data = {'project_name': "test_project", 'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        new_task = Task.objects.all()[0]
        url = "/v1/tasks/" + new_task.uuid
        response = self.client.post(url, {'approved': True}, format='json',
                                    headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(Token.objects.all()), 1)

        new_token = Token.objects.all()[0]
        url = "/v1/tokens/" + new_token.token
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Reapprove
        url = "/v1/tasks/" + new_task.uuid
        response = self.client.post(url, {'approved': True}, format='json',
                                    headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Old token no longer found
        url = "/v1/tokens/" + new_token.token
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(len(Token.objects.all()), 1)

    def test_task_update_unapprove(self):
        """
        Ensure task update doesn't work for approved actions.
        """

        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        setup_temp_cache({}, {})

        url = "/v1/actions/CreateProject"
        data = {'project_name': "test_project", 'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }

        new_task = Task.objects.all()[0]
        url = "/v1/tasks/" + new_task.uuid
        response = self.client.post(url, {'approved': True}, format='json',
                                    headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_task = Task.objects.all()[0]
        self.assertEqual(new_task.approved, True)

        data = {'project_name': "test_project2", 'email': "test2@example.com"}
        response = self.client.put(url, data, format='json',
                                   headers=headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_task_own(self):
        """
        Ensure the ability to cancel your own task.
        """

        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        setup_temp_cache({'test_project': project}, {})

        url = "/v1/actions/InviteUser"
        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "project_admin,_member_,project_mod",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        data = {'email': "test@example.com", 'roles': ["_member_"],
                'project_id': 'test_project_id'}
        response = self.client.post(url, data, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'notes': ['created token']})

        new_task = Task.objects.all()[0]
        url = "/v1/tasks/" + new_task.uuid
        response = self.client.delete(url, format='json',
                                      headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        headers['roles'] = "admin"
        response = self.client.post(url, {'approved': True}, format='json',
                                    headers=headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.put(url, format='json',
                                   headers=headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_task_own_fail(self):
        """
        Ensure the ability to cancel ONLY your own task.
        """

        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        setup_temp_cache({'test_project': project}, {})

        url = "/v1/actions/InviteUser"
        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "project_admin,_member_,project_mod",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        data = {'email': "test@example.com", 'roles': ["_member_"],
                'project_id': 'test_project_id'}
        response = self.client.post(url, data, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'notes': ['created token']})

        new_task = Task.objects.all()[0]
        url = "/v1/tasks/" + new_task.uuid
        headers['project_id'] = "fake_project_id"
        response = self.client.delete(url, format='json',
                                      headers=headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_task_list(self):
        """
        """
        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        setup_temp_cache({'test_project': project}, {})

        url = "/v1/actions/InviteUser"
        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "project_admin,_member_,project_mod",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        data = {'email': "test@example.com", 'roles': ["_member_"],
                'project_id': 'test_project_id'}
        response = self.client.post(url, data, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = {'email': "test2@example.com", 'roles': ["_member_"],
                'project_id': 'test_project_id'}
        response = self.client.post(url, data, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = {'email': "test3@example.com", 'roles': ["_member_"],
                'project_id': 'test_project_id'}
        response = self.client.post(url, data, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        url = "/v1/tasks"
        response = self.client.get(url, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()['tasks']), 3)

    def test_task_list_ordering(self):
        """
        Test that tasks returns in the default sort.
        The default sort is by created_on descending.
        """
        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        setup_temp_cache({'test_project': project}, {})

        url = "/v1/actions/InviteUser"
        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "project_admin,_member_,project_mod",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        data = {'email': "test@example.com", 'roles': ["_member_"],
                'project_id': 'test_project_id'}
        response = self.client.post(url, data, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = {'email': "test2@example.com", 'roles': ["_member_"],
                'project_id': 'test_project_id'}
        response = self.client.post(url, data, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = {'email': "test3@example.com", 'roles': ["_member_"],
                'project_id': 'test_project_id'}
        response = self.client.post(url, data, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        url = "/v1/tasks"
        response = self.client.get(url, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sorted_list = sorted(
            response.json()['tasks'],
            key=lambda k: k['created_on'],
            reverse=True)

        for i, task in enumerate(sorted_list):
            self.assertEqual(task, response.json()['tasks'][i])

    def test_task_list_filter(self):
        """
        """
        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        setup_temp_cache({'test_project': project}, {})

        url = "/v1/actions/InviteUser"
        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "project_admin,_member_,project_mod",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        data = {'email': "test@example.com", 'roles': ["_member_"],
                'project_id': 'test_project_id'}
        response = self.client.post(url, data, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = {'email': "test2@example.com", 'roles': ["_member_"],
                'project_id': 'test_project_id'}
        response = self.client.post(url, data, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        url = "/v1/actions/CreateProject"
        data = {'project_name': "test_project2", 'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        params = {
            "filters": json.dumps({
                "task_type": {"exact": "create_project"}
            })
        }

        url = "/v1/tasks"
        response = self.client.get(
            url, params, format='json', headers=headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()['tasks']), 1)

        params = {
            "filters": json.dumps({
                "task_type": {"exact": "invite_user"}
            })
        }
        response = self.client.get(
            url, params, format='json', headers=headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()['tasks']), 2)

    # TODO(adriant): enable this test again when filters are properly
    # blacklisted.
    @skip("Does not apply yet.")
    def test_task_list_filter_cross_project(self):
        """
        Ensure you can't override the initial project_id filter if
        you are not admin.
        """

        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        project2 = mock.Mock()
        project2.id = 'test_project_id_2'
        project2.name = 'test_project_2'
        project2.domain = 'default'
        project2.roles = {}

        setup_temp_cache(
            {'test_project': project, 'test_project_2': project2}, {})

        url = "/v1/actions/InviteUser"
        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "project_admin,_member_,project_mod",
            'username': "owner@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        data = {'email': "test@example.com", 'roles': ["_member_"],
                'project_id': 'test_project_id'}
        response = self.client.post(url, data, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id_2",
            'roles': "project_admin,_member_,project_mod",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }

        params = {
            "filters": json.dumps({
                "project_id": {"exact": "test_project_id"},
                "task_type": {"exact": "invite_user"}
            })
        }
        url = "/v1/tasks"
        response = self.client.get(
            url, params, format='json', headers=headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()['tasks']), 0)

    def test_task_list_filter_formating(self):
        """
        """
        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {}

        setup_temp_cache({'test_project': project}, {})

        url = "/v1/actions/InviteUser"
        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "project_admin,_member_,project_mod",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }
        data = {'email': "test@example.com", 'roles': ["_member_"],
                'project_id': 'test_project_id'}
        response = self.client.post(url, data, format='json', headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        headers = {
            'project_name': "test_project",
            'project_id': "test_project_id",
            'roles': "admin,_member_",
            'username': "test@example.com",
            'user_id': "test_user_id",
            'authenticated': True
        }

        # not proper json
        params = {
            "filters": {
                "task_type": {"exact": "create_project"}
            }
        }
        url = "/v1/tasks"
        response = self.client.get(
            url, params, format='json', headers=headers
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # inncorrect format
        params = {
            "filters": json.dumps("gibbberish")
        }
        response = self.client.get(
            url, params, format='json', headers=headers
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # inncorrect format
        params = {
            "filters": json.dumps({
                "task_type": ["exact", "value"]
            })
        }
        response = self.client.get(
            url, params, format='json', headers=headers
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # invalid operation
        params = {
            "filters": json.dumps({
                "task_type": {"dont_find": "value"}
            })
        }
        response = self.client.get(
            url, params, format='json', headers=headers
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # invalid field
        params = {
            "filters": json.dumps({
                "fake": {"exact": "value"}
            })
        }
        response = self.client.get(
            url, params, format='json', headers=headers
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @modify_dict_settings(TASK_SETTINGS={
        'key_list': ['reset_password', 'action_settings',
                     'ResetUserPasswordAction', 'blacklisted_roles'],
        'operation': 'append',
        'value': ['admin']
    })
    def test_reset_admin(self):
        """
        Ensure that you cannot issue a password reset for an
        admin user.
        """

        user = mock.Mock()
        user.id = 'user_id'
        user.name = "test@example.com"
        user.email = "test@example.com"
        user.domain = 'default'
        user.password = "test_password"

        project = mock.Mock()
        project.id = 'test_project_id'
        project.name = 'test_project'
        project.domain = 'default'
        project.roles = {user.id: ['admin']}

        setup_temp_cache({'test_project': project}, {user.id: user})

        url = "/v1/actions/ResetPassword"
        data = {'email': "test@example.com"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()['notes'],
            ['If user with email exists, reset token will be issued.'])
        self.assertEqual(0, Token.objects.count())
