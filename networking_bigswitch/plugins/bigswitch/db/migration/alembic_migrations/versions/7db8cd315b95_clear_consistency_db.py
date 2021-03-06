# Copyright 2014 Big Switch Networks, Inc.
# All Rights Reserved.
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

"""clear consistency_db

Revision ID: 7db8cd315b95
Revises: 2dc6f1b7c0a1
Create Date: 2018-05-08 12:38:56.871617

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '7db8cd315b95'
down_revision = '2dc6f1b7c0a1'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    connection.execute("TRUNCATE TABLE consistencyhashes;")
