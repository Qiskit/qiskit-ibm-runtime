onsiderations for using Qiskit Runtime in an organization
==========================================================

You should understand the following considerations when setting up your environment.

Auditability
------------

Activity tracker logs significant actions performed on Qiskit Runtime service instances. Create an instance of Activity Tracker in the region of your Qiskit Runtime instances to get an audit trail of events. Refer to the Qiskit Runtime `Activity Tracker page <at_events>`__ for details about the events logged.

This audit log contains the fields ``initiator_authnName`` and ``initiator_authnId``, which match the name shown in `Manage → Access (IAM) → Users <https://cloud.ibm.com/iam/users>`__. To view this field, click on the user name, then **Details** in the **IAM ID** field.

|event|

To capture App ID events, open your App ID instance, then navigate to **Manage Authentication -> Authentication settings** and enable **Runtime Activity**.

Define more fine grained roles
------------------------------

The actions in the custom roles can be used for more fine grained access control. For example, some users might need full access to work on service instances, while others might only need Read access to service instances, programs, and jobs.

To achieve that, define two different custom roles such as ``MLreader`` and ``MLwriter``. Remove all cancel, delete, and update roles from the ``MLreader`` custom role, and include all actions in the ``MLwriter`` custom role. Next, add the roles to two different access groups accordingly.

When using dynamic rules, that is, when the IDP administrator manages access through custom IDP user attributes, do not use IDP custom user attributes that are substrings of each other. For instance, don’t use ``ml`` and ``mlReader``, as the string comparison of ``ml`` would also accept ``mlReader``. You could use ``MLreader`` and ``MLwriter`` to avoid this conflict. {: note}

For an example of setting up custom roles, see `Create access groups for projects <quickstart-steps-org#create-group-org>`__.

Other Cloud resources
---------------------

The steps used in this tutorial can be used to manage access to other Cloud resources as well. Include the appropriate permissions to the access groups of the relevant projects.

Hierarchical project structures
-------------------------------

In this tutorial, the mapping of users to projects and service instances was kept simple. However, by associating several users with access groups and referencing service instances from several access groups, more complex mappings can be implemented.

This method can accommodate a hierarchical structure. That is, it can align to how users might be assigned to the Hub/Group/Project access structure in the IBM Quantum Platform. For example, a *group* could be an access group that is assigned to all service instances of the group’s projects. Users who should get access to all of the group’s projects would then only have to be added to the group’s access group.

Consistent and repeatable deployment of the configuration
---------------------------------------------------------

The steps of this tutorial can be automated for consistent and repeatable management of users, projects, and the mapping between those. Refer to the `Terraform IBM Cloud Provider documentation <https://registry.terraform.io/providers/IBM-Cloud/ibm/latest/docs>`__ for templates.

.. |event| image:: images/org-guide-audit-example.png