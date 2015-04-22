# -*- coding: utf-8 -*-
import logging
from util import full_stack
from util import exec_remote_command
from util import build_context_script
from dbaas_cloudstack.models import HostAttr as CS_HostAttr
from ...util.base import BaseStep
from ....exceptions.error_codes import DBAAS_0019

LOG = logging.getLogger(__name__)


class AddInstancesReplicaSet(BaseStep):

    def __unicode__(self):
        return "Adding instances to replica set..."

    def do(self, workflow_dict):
        try:

            initial_script = '#!/bin/bash\n\ndie_if_error()\n{\n    local err=$?\n    if [ "$err" != "0" ]; then\n        echo "$*"\n        exit $err\n    fi\n}'
            databaseinfra = workflow_dict['databaseinfra']
            
            connect_string = ""
            for source_instance in workflow_dict['source_instances']:
                if source_instance.instance_type != source_instance.MONGODB_ARBITER:
                    if connect_string:
                        connect_string += ','
                    connect_string += source_instance.address + ":" + str(source_instance.port)
            
            connect_string = databaseinfra.get_driver().get_replica_name() + "/" + connect_string
            connect_string = " --host {} admin -u{} -p{}".format(connect_string, databaseinfra.user, databaseinfra.password)
            LOG.debug(connect_string)
            
            client = databaseinfra.get_driver().get_client(None)
            rsconf = client.local.system.replset.find_one()
            member_ids = []
            for member in rsconf['members']:
                member_ids.append(member['_id'])
            
            max_member_id = max(member_ids)
            secundary_one_member_id = max_member_id + 1
            secundary_two_member_id = max_member_id + 2
            
            context_dict = {
                    'CONNECT_STRING': connect_string,
                    'SECUNDARY_ONE': "{}:{}".format(workflow_dict['target_instances'][0].address, workflow_dict['target_instances'][0].port),
                    'SECUNDARY_TWO': "{}:{}".format(workflow_dict['target_instances'][1].address, workflow_dict['target_instances'][1].port),
                    'ARBITER': "{}:{}".format(workflow_dict['target_instances'][2].address, workflow_dict['target_instances'][2].port),
                    'SECUNDARY_ONE_MEMBER_ID': secundary_one_member_id,
                    'SECUNDARY_TWO_MEMBER_ID': secundary_two_member_id,
                }

            script = initial_script
            script += '\necho ""; echo $(date "+%Y-%m-%d %T") "- Adding new database members"'
            script += '\n/usr/local/mongodb/bin/mongo {{CONNECT_STRING}} <<EOF_DBAAS'
            script += '\nrs.add( { "_id": {{SECUNDARY_ONE_MEMBER_ID}}, "host": "{{SECUNDARY_ONE}}", "priority": 0 } )'
            script += '\nrs.add( { "_id": {{SECUNDARY_TWO_MEMBER_ID}}, "host": "{{SECUNDARY_TWO}}", "priority": 0 } )'
            script += '\nrs.addArb("{{ARBITER}}")'
            script += '\nexit'
            script += '\nEOF_DBAAS'
            script += '\ndie_if_error "Error adding new replica set members"'

            script = build_context_script(context_dict, script)
            output = {}

            host = workflow_dict['source_instances'][0].hostname
            cs_host_attr = CS_HostAttr.objects.get(host=host)

            return_code = exec_remote_command(server=host.address,
                                              username=cs_host_attr.vm_user,
                                              password=cs_host_attr.vm_password,
                                              command=script,
                                              output=output)
            LOG.info(output)
            if return_code != 0:
                raise Exception, str(output)

            return True
        except Exception:
            traceback = full_stack()

            workflow_dict['exceptions']['error_codes'].append(DBAAS_0019)
            workflow_dict['exceptions']['traceback'].append(traceback)

            return False

    def undo(self, workflow_dict):
        LOG.info("Running undo...")
        try:

            initial_script = '#!/bin/bash\n\ndie_if_error()\n{\n    local err=$?\n    if [ "$err" != "0" ]; then\n        echo "$*"\n        exit $err\n    fi\n}'
            databaseinfra = workflow_dict['databaseinfra']

            connect_string = ""
            for source_instance in workflow_dict['source_instances']:
                if source_instance.instance_type != source_instance.MONGODB_ARBITER:
                    if connect_string:
                        connect_string += ','
                    connect_string += source_instance.address + ":" + str(source_instance.port)

            connect_string = databaseinfra.get_driver().get_replica_name() + "/" + connect_string
            connect_string = " --host {} admin -u{} -p{}".format(connect_string, databaseinfra.user, databaseinfra.password)
            LOG.debug(connect_string)

            context_dict = {
                    'CONNECT_STRING': connect_string,
                    'SECUNDARY_ONE': "{}:{}".format(workflow_dict['target_instances'][0].address, workflow_dict['target_instances'][0].port),
                    'SECUNDARY_TWO': "{}:{}".format(workflow_dict['target_instances'][1].address, workflow_dict['target_instances'][1].port),
                    'ARBITER': "{}:{}".format(workflow_dict['target_instances'][2].address, workflow_dict['target_instances'][2].port),
                }

            script = initial_script
            script += '\necho ""; echo $(date "+%Y-%m-%d %T") "- Removing new database members"'
            script += '\n/usr/local/mongodb/bin/mongo {{CONNECT_STRING}} <<EOF_DBAAS'
            script += '\nrs.remove("{{ARBITER}}")'
            script += '\nexit'
            script += '\nEOF_DBAAS'
            script += '\ndie_if_error "Error removing new replica set members"'

            script += '\nsleep 30'
            script += '\necho ""; echo $(date "+%Y-%m-%d %T") "- Removing new database members"'
            script += '\n/usr/local/mongodb/bin/mongo {{CONNECT_STRING}} <<EOF_DBAAS'
            script += '\nrs.remove("{{SECUNDARY_TWO}}")'
            script += '\nexit'
            script += '\nEOF_DBAAS'
            script += '\ndie_if_error "Error removing new replica set members"'

            script += '\nsleep 30'
            script += '\necho ""; echo $(date "+%Y-%m-%d %T") "- Removing new database members"'
            script += '\n/usr/local/mongodb/bin/mongo {{CONNECT_STRING}} <<EOF_DBAAS'
            script += '\nrs.remove("{{SECUNDARY_ONE}}")'
            script += '\nexit'
            script += '\nEOF_DBAAS'
            script += '\ndie_if_error "Error removing new replica set members"'

            
            script = build_context_script(context_dict, script)
            output = {}

            host = workflow_dict['source_instances'][0].hostname
            cs_host_attr = CS_HostAttr.objects.get(host=host)
            return_code = exec_remote_command(server=host.address,
                                              username=cs_host_attr.vm_user,
                                              password=cs_host_attr.vm_password,
                                              command=script,
                                              output=output)
            LOG.info(output)
            if return_code != 0:
                raise Exception, str(output)

            return True
        except Exception:
            traceback = full_stack()

            workflow_dict['exceptions']['error_codes'].append(DBAAS_0019)
            workflow_dict['exceptions']['traceback'].append(traceback)

            return False