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

SECRET_KEY = '+er!!4olta#17a=n%uotcazg2ncpl==yjog%1*o-(cr%zys-)!'

ADDITIONAL_APPS = [
    'stacktask.api.v1',
    'stacktask.tenant_setup'
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3'
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'reg_log.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'keystonemiddleware': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

EMAIL_SETTINGS = {
    "EMAIL_BACKEND": "django.core.mail.backends.console.EmailBackend"
}

# setting to control if user name and email are allowed
# to have different values.
USERNAME_IS_EMAIL = True

# Keystone admin credentials:
KEYSTONE = {
    'username': 'admin',
    'password': 'openstack',
    'project_name': 'admin',
    'auth_url': "http://localhost:5000/v2.0"
}

DEFAULT_REGION = 'RegionOne'

# Additonal actions for views:
# - The order of the actions matters. These will run after the default action,
#   in the given order.
ACTIONVIEW_SETTINGS = {
    'AttachUser': {
        'emails': {
            'token': {
                'reply': 'no-reply@example.com',
                'html_template': 'token.txt',
                'template': 'token.txt',
                'subject': 'Your Token'
            },
            'initial': None,
            'completed': {
                'reply': 'no-reply@example.com',
                'html_template': 'completed.txt',
                'template': 'completed.txt',
                'subject': 'Task completed'
            }
        }
    },
    'CreateProject': {
        'emails': {
            'token': {
                'reply': 'no-reply@example.com',
                'html_template': 'token.txt',
                'template': 'token.txt',
                'subject': 'Your Token'
            },
            'initial': {
                'reply': 'no-reply@example.com',
                'html_template': 'initial.txt',
                'template': 'initial.txt',
                'subject': 'Initial Confirmation'
            },
            'completed': {
                'reply': 'no-reply@example.com',
                'html_template': 'completed.txt',
                'template': 'completed.txt',
                'subject': 'Task completed'
            }
        },
        'actions': [
            'AddAdminToProject',
            'DefaultProjectResources'
        ]
    },
    'ResetPassword': {
        'emails': {
            'token': {
                'reply': 'no-reply@example.com',
                'html_template': 'token.txt',
                'template': 'token.txt',
                'subject': 'Your Token'
            },
            'completed': {
                'reply': 'no-reply@example.com',
                'html_template': 'completed.txt',
                'template': 'completed.txt',
                'subject': 'Task completed'
            }
        }
    }
}

ACTION_SETTINGS = {
    'NewUser': {
        'allowed_roles': ['project_mod', 'project_owner', "Member"]
    },
    'DefaultProjectResources': {
        'RegionOne': {
            'DNS_NAMESERVERS': ['193.168.1.2', '193.168.1.3'],
            'SUBNET_CIDR': '192.168.1.0/24',
            'network_name': 'somenetwork',
            'public_network': '3cb50f61-5bce-4c03-96e6-8e262e12bb35',
            'router_name': 'somerouter',
            'subnet_name': 'somesubnet'
        }
    }
}

conf_dict = {
    "SECRET_KEY": SECRET_KEY,
    "ADDITIONAL_APPS": ADDITIONAL_APPS,
    "DATABASES": DATABASES,
    "LOGGING": LOGGING,
    "EMAIL_SETTINGS": EMAIL_SETTINGS,
    "USERNAME_IS_EMAIL": USERNAME_IS_EMAIL,
    "KEYSTONE": KEYSTONE,
    "DEFAULT_REGION": DEFAULT_REGION,
    "ACTIONVIEW_SETTINGS": ACTIONVIEW_SETTINGS,
    "ACTION_SETTINGS": ACTION_SETTINGS
}