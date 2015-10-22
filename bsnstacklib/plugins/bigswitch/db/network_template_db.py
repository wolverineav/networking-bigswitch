# Copyright Big Switch Networks 2014

import sqlalchemy as sa
from neutron.db import model_base


class NetworkTemplate(model_base.BASEV2):
    __tablename__ = 'networktemplates'
    __table_args__ = {'extend_existing': True}
    id = sa.Column(sa.Integer, primary_key=True)
    tenant_id = sa.Column(sa.String(255), nullable=False)
    body = sa.Column(sa.Text(), nullable=False)
    template_name = sa.Column(sa.String(255), nullable=False, unique=True)


class NetworkTemplateAssignment(model_base.BASEV2):
    __tablename__ = 'networktemplateassignments'
    __table_args__ = {'extend_existing': True}
    template_id = sa.Column(sa.Integer, sa.ForeignKey('networktemplates.id'),
                            nullable=False)
    tenant_id = sa.Column(sa.String(255), nullable=False, primary_key=True)
    stack_id = sa.Column(sa.String(255), nullable=False)
    template = sa.orm.relationship("NetworkTemplate")
