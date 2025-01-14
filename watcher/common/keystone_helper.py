# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from oslo_log import log

from keystoneauth1.exceptions import http as ks_exceptions
from keystoneauth1 import loading
from keystoneauth1 import session
from watcher._i18n import _
from watcher.common import clients
from watcher.common import exception
from watcher import conf

CONF = conf.CONF
LOG = log.getLogger(__name__)


class KeystoneHelper(object):

    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        self.osc = osc if osc else clients.OpenStackClients()
        self.keystone = self.osc.keystone()

    def get_role(self, name_or_id):
        try:
            role = self.keystone.roles.get(name_or_id)
            return role
        except ks_exceptions.NotFound:
            roles = self.keystone.roles.list(name=name_or_id)
            if len(roles) == 0:
                raise exception.Invalid(
                    message=(_("Role not Found: %s") % name_or_id))
            if len(roles) > 1:
                raise exception.Invalid(
                    message=(_("Role name seems ambiguous: %s") % name_or_id))
        return roles[0]

    def get_user(self, name_or_id):
        try:
            user = self.keystone.users.get(name_or_id)
            return user
        except ks_exceptions.NotFound:
            users = self.keystone.users.list(name=name_or_id)
            if len(users) == 0:
                raise exception.Invalid(
                    message=(_("User not Found: %s") % name_or_id))
            if len(users) > 1:
                raise exception.Invalid(
                    message=(_("User name seems ambiguous: %s") % name_or_id))
            return users[0]

    def get_project(self, name_or_id):
        try:
            project = self.keystone.projects.get(name_or_id)
            return project
        except ks_exceptions.NotFound:
            projects = self.keystone.projects.list(name=name_or_id)
            if len(projects) == 0:
                raise exception.Invalid(
                    message=(_("Project not Found: %s") % name_or_id))
            if len(projects) > 1:
                raise exception.Invalid(
                    message=(_("Project name seems ambiguous: %s") %
                             name_or_id))
            return projects[0]

    def get_domain(self, name_or_id):
        try:
            domain = self.keystone.domains.get(name_or_id)
            return domain
        except ks_exceptions.NotFound:
            domains = self.keystone.domains.list(name=name_or_id)
            if len(domains) == 0:
                raise exception.Invalid(
                    message=(_("Domain not Found: %s") % name_or_id))
            if len(domains) > 1:
                raise exception.Invalid(
                    message=(_("Domain name seems ambiguous: %s") %
                             name_or_id))
            return domains[0]

    def create_session(self, user_id, password):
        user = self.get_user(user_id)
        loader = loading.get_plugin_loader('password')
        auth = loader.load_from_options(
            auth_url=CONF.watcher_clients_auth.auth_url,
            password=password,
            user_id=user_id,
            project_id=user.default_project_id)
        return session.Session(auth=auth)

    def create_user(self, user):
        project = self.get_project(user['project'])
        domain = self.get_domain(user['domain'])
        _user = self.keystone.users.create(
            user['name'],
            password=user['password'],
            domain=domain,
            project=project,
        )
        for role in user['roles']:
            role = self.get_role(role)
            self.keystone.roles.grant(
                role.id, user=_user.id, project=project.id)
        return _user

    def delete_user(self, user):
        try:
            user = self.get_user(user)
            self.keystone.users.delete(user)
        except exception.Invalid:
            pass
