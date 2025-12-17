# Copyright Amazon.com Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may
# not use this file except in compliance with the License. A copy of the
# License is located at
#
#	 http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

"""Integration tests for the ReusableDelegationSet resource"""

import time
import pytest

from acktest.resources import random_suffix_name
from acktest.k8s import resource as k8s

from e2e import service_marker, CRD_GROUP, CRD_VERSION, load_resource
from e2e.replacement_values import REPLACEMENT_VALUES

RESOURCE_PLURAL = "reusabledelegationsets"

@service_marker
@pytest.mark.canary
class TestReusableDelegationSet:
    def test_crud(self, route53_client):
        resource_name = random_suffix_name("delegation-set", 24)
        caller_ref = str(time.time())

        replacements = REPLACEMENT_VALUES.copy()
        replacements["REUSABLE_DELEGATION_SET_NAME"] = resource_name
        replacements["CALLER_REFERENCE"] = caller_ref

        resource_data = load_resource(
            "reusable_delegation_set", additional_replacements=replacements,
        )

        ref = k8s.CustomResourceReference(
            CRD_GROUP, CRD_VERSION, RESOURCE_PLURAL, resource_name, namespace="default",
        )
        k8s.create_custom_resource(ref, resource_data)
        cr = k8s.wait_resource_consumed_by_controller(ref)

        assert cr is not None
        assert k8s.get_resource_exists(ref)

        # Check AWS
        # Note: Route53 ReusableDelegationSets are identified by ID, which is in status
        delegation_set_id = cr["status"]["id"]
        assert delegation_set_id is not None

        try:
            aws_res = route53_client.get_reusable_delegation_set(Id=delegation_set_id)
            assert aws_res is not None
            assert aws_res["DelegationSet"]["CallerReference"] == caller_ref
        except Exception as e:
            pytest.fail(f"Could not find ReusableDelegationSet in AWS: {e}")

        # Delete
        k8s.delete_custom_resource(ref)
        time.sleep(10) # Wait for deletion

        # Verify deletion
        assert not k8s.get_resource_exists(ref)

        try:
            route53_client.get_reusable_delegation_set(Id=delegation_set_id)
            pytest.fail("ReusableDelegationSet should be deleted in AWS")
        except route53_client.exceptions.DelegationSetNotReusable:
            pass # Expected if it's gone? No, Get returns NoSuchDelegationSet usually
        except route53_client.exceptions.NoSuchDelegationSet:
            pass
        except Exception as e:
            # Depending on error code, it might be different
            if "NoSuchDelegationSet" in str(e):
                pass
            else:
                raise e


