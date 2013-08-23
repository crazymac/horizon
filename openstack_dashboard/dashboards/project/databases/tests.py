# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Mirantis Inc.
# Copyright 2013 Rackspace Hosting.
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

from django.core.urlresolvers import reverse
from django import http
from django.utils.datastructures import SortedDict
from mox import IsA

from openstack_dashboard import api
from openstack_dashboard.test import helpers as test


INDEX_URL = reverse('horizon:project:databases:index')
LAUNCH_URL = reverse('horizon:project:databases:launch')
DETAILS_URL = reverse('horizon:project:databases:detail', args=['id'])


class DatabaseTests(test.TestCase):

    @test.create_stubs(
        {api.trove: ('instance_list', 'flavor_list', 'flavor_get')})
    def test_index(self):
        # Mock database instances
        api.trove.instance_list(
            IsA(http.HttpRequest), marker=None)\
            .AndReturn(self.databases.list())
        # Mock flavors
        api.trove.flavor_list(IsA(http.HttpRequest))\
            .AndReturn(self.flavors.list())
        api.trove.flavor_get(IsA(http.HttpRequest), IsA(str))\
            .AndReturn(self.flavors.first())

        self.mox.ReplayAll()
        res = self.client.get(INDEX_URL)
        self.assertTemplateUsed(res, 'project/databases/index.html')

    @test.create_stubs(
        {api.trove: ('instance_list', 'flavor_list', 'flavor_get')})
    def test_index_exception(self):
        trove_exception = self.exceptions.nova
        # Mock database instances
        api.trove.instance_list(
            IsA(http.HttpRequest), marker=None)\
            .AndReturn(self.databases.list())
        # Mock flavors
        api.trove.flavor_list(IsA(http.HttpRequest))\
            .AndRaise(trove_exception)
        api.trove.flavor_get(IsA(http.HttpRequest), IsA(str))\
            .AndReturn(self.flavors.first())

        self.mox.ReplayAll()
        res = self.client.get(INDEX_URL)
        self.assertTemplateUsed(res, 'project/databases/index.html')

    @test.create_stubs(
        {api.trove: ('instance_list', 'flavor_list', 'flavor_get')})
    def test_index_flavor_list_exception(self):
        trove_exception = self.exceptions.nova
        databases = self.databases.list()
        flavors = self.flavors.list()
        fullFlavors = SortedDict([(f.id, f) for f in flavors])
        #Mocking instances
        api.trove.instance_list(
            IsA(http.HttpRequest), marker=None)\
            .AndReturn(self.databases.list())
        #Mocking flavor list with raising an exception
        api.trove.flavor_list(IsA(http.HttpRequest))\
            .AndRaise(trove_exception)

        for database in databases:
            api.trove.flavor_get(IsA(http.HttpRequest),
                                 database.flavor['id']) \
                .AndReturn(fullFlavors['aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'])

        self.mox.ReplayAll()

        res = self.client.get(INDEX_URL)

        self.assertTemplateUsed(res, 'project/databases/index.html')

    @test.create_stubs(
        {api.trove: ('instance_list', 'flavor_list', 'flavor_get')})
    def test_index_flavor_get_exception(self):
        trove_exception = self.exceptions.nova
        databases = self.databases.list()
        flavors = self.flavors.list()
        #Mocking instances
        api.trove.instance_list(
            IsA(http.HttpRequest), marker=None)\
            .AndReturn(self.databases.list())
        api.trove.flavor_list(IsA(http.HttpRequest))\
            .AndReturn(self.flavors.list())
        for database in databases:
            api.trove.flavor_get(IsA(http.HttpRequest),
                                 database.flavor['id']) \
                .AndRaise(trove_exception)

        self.mox.ReplayAll()
        res = self.client.get(INDEX_URL)

        self.assertMessageCount(res, error=len(databases))
        self.assertItemsEqual(databases, self.databases.list())

    @test.create_stubs({
        api.nova: ('flavor_list', 'tenant_absolute_limits'),
        api.trove: ('backup_list',)})
    def test_launch_instance(self):
        api.nova.flavor_list(IsA(http.HttpRequest))\
            .AndReturn(self.flavors.list())
        api.nova.tenant_absolute_limits(IsA(http.HttpRequest))\
            .AndReturn([])
        api.trove.backup_list(IsA(http.HttpRequest))\
            .AndReturn(self.database_backups.list())

        self.mox.ReplayAll()
        res = self.client.get(LAUNCH_URL)
        self.assertTemplateUsed(res, 'project/databases/launch.html')

    @test.create_stubs({
        api.nova: ('flavor_list', 'tenant_absolute_limits'),
        api.trove: ('backup_list',)})
    def test_launch_instance(self):
        trove_exception = self.exceptions.nova
        api.nova.flavor_list(IsA(http.HttpRequest))\
            .AndRaise(self.exceptions.nova)
        api.nova.tenant_absolute_limits(IsA(http.HttpRequest))\
            .AndRaise(trove_exception)
        api.trove.backup_list(IsA(http.HttpRequest))\
            .AndReturn(self.database_backups.list())

        self.mox.ReplayAll()
        res = self.client.get(LAUNCH_URL)
        self.assertTemplateUsed(res, 'project/databases/launch.html')

    @test.create_stubs({
        api.nova: ('flavor_list',),
        api.trove: ('backup_list', 'instance_create',)})
    def test_create_simple_instance(self):
        api.nova.flavor_list(IsA(http.HttpRequest))\
            .AndReturn(self.flavors.list())
        api.trove.backup_list(IsA(http.HttpRequest))\
            .AndReturn(self.database_backups.list())

        # Actual create database call
        api.trove.instance_create(
            IsA(http.HttpRequest),
            IsA(unicode),
            IsA(int),
            IsA(unicode),
            databases=None,
            restore_point=None,
            users=None).AndReturn(self.databases.first())

        self.mox.ReplayAll()
        post = {
            'name': "MyDB",
            'volume': '1',
            'flavor': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        }

        res = self.client.post(LAUNCH_URL, post)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({
        api.nova: ('flavor_list',),
        api.trove: ('backup_list', 'instance_create',)})
    def test_create_simple_instance_exception(self):
        trove_exception = self.exceptions.nova
        api.nova.flavor_list(IsA(http.HttpRequest))\
            .AndReturn(self.flavors.list())
        api.trove.backup_list(IsA(http.HttpRequest))\
            .AndReturn(self.database_backups.list())

        # Actual create database call
        api.trove.instance_create(
            IsA(http.HttpRequest),
            IsA(unicode),
            IsA(int),
            IsA(unicode),
            databases=None,
            restore_point=None,
            users=None).AndRaise(trove_exception)

        self.mox.ReplayAll()
        post = {
            'name': "MyDB",
            'volume': '1',
            'flavor': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        }

        res = self.client.post(LAUNCH_URL, post)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs(
        {api.trove: ('instance_get', 'flavor_get',)})
    def test_details(self):
        api.trove.instance_get(IsA(http.HttpRequest), IsA(unicode))\
            .AndReturn(self.databases.first())
        api.trove.flavor_get(IsA(http.HttpRequest), IsA(str))\
            .AndReturn(self.flavors.first())

        self.mox.ReplayAll()
        res = self.client.get(DETAILS_URL)
        self.assertTemplateUsed(res, 'project/databases/detail.html')