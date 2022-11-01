Manage ID provider users with IBM Cloud
=======================================

App ID creates an ID provider so you can add users directly in App ID or connect to other external ID providers. This tutorial describes how to set up your ID provider to work with IBM Cloud users, and gives instructions for users to access the environment.

To manage users in a different way, follow the instructions in one of these topics:

-  `Manage IBM Cloud users <cloud-provider-org>`__
-  `Manage ID provider users with the ID provider <appid-org>`__

Create an App ID instance
-------------------------

1. `Open App ID from the IBM Cloud catalog <https://cloud.ibm.com/catalog/services/app-id>`__ and log in if necessary. Specify the following values:

   -  For **Select a location**, it is recommended that you keep it in the same location as the Qiskit Runtime service, which is ``Washington DC (us-east)``.
   -  **Select a pricing plan**:

      -  The **Lite** plan is free of charge and is enough to get started. If needed, you can seamlessly upgrade to the graduated tier later.
      -  The **Graduated tier** is paid per event and per user beyond the lite tier limits. This tier supports more features such as multi-factor authentication. The Cloud administrator as the owning account of the App ID instance is charged for any fees for the graduated tier instances.

   -  Complete the values for **Service name** (the App ID instance name), **Resource group** (if one is being used), and any tags you want.

   |create|

2. Read and agree to the terms and click **Create**.

Configure the ID provider
-------------------------

We will use the **Cloud Directory** capability to add users to the ID provider. Refer to the `App ID documentation <https://cloud.ibm.com/docs/appid>`__ for instructions how to integrate other ID providers into App ID.

1. Open the `IBM Cloud resource list <https://cloud.ibm.com/resources>`__, expand the **Services and software** section, find your App ID instance and click its name to view its details.
2. Click **Manage Authentication** and deselect any login options that you don’t need, such as Facebook and Google.
3. Go to **Manage Authentication** → **Cloud Directory** → **Settings** and choose whether user logins should use email or usernames.
4. Optionally go to **Manage Authentication** → **Cloud Directory** → **Password Policies** to define the password strength.
5. Optionally open **Login Customization** and customize the appearance of the login page.

Integrate the App ID instance as the ID provider for the administrator’s account
--------------------------------------------------------------------------------

1. Go to `Manage → Access (IAM) → Identity Providers <https://cloud.ibm.com/iam/identity-providers>`__. For **Type**, choose **IBM Cloud App ID**, then click **Create**.

2. Specify a name and select the App ID instance from the drop-down list.

3. Select the checkbox to enable the ID provider.

   |identity|

4. The default IdP URL is shown. Share this URL with users when they need to log in.

Add Users
---------

When you use App ID as ID provider with the Cloud directory, you can create users in the IBM Cloud user interface.

1. Open the App ID instance page from the `resource list <https://cloud.ibm.com/resources>`__ Services and software section.
2. Go to **Manage Authentication** → **Cloud Directory** → **Users**, and click **Create User**. Enter the user details.

Create or modify users’ project assignments
-------------------------------------------

1. Go to `Manage → Access (IAM) → Users <https://cloud.ibm.com/iam/users>`__ and click the user. 

   |access|
   
   .. note::
      If you don’t see the user that you want to manage, verify that they logged in to IBM Cloud at least once. See step 1 in the :ref:`user-org`.

2. Add access groups with **Assign group** or remove the user from an access group by clicking the three dot menu and choosing **Remove user**.

.. user-org:

User flow
---------

1. A user is sent the ID provider URL for the IBM Cloud account. They use this URL and the login information to access the system. The user should change their password after they log on.

   .. note::
      The administrator can always go to `Manage → Access (IAM) → Identity providers <https://cloud.ibm.com/iam/identity-providers>`__ to look up the ID provider URL.

2. To work with Qiskit Runtime and access service instances, users need to create an API key from `Manage → Access (IAM) → API keys <https://cloud.ibm.com/iam/apikeys>`__.

3. For further information, users can review `Getting started, Step 2 <quickstart#install-packages>`__.

Example scenario
----------------

In our example, we want to create the following setup:

-  We have two projects, ``ml`` and ``finance``.

   -  The ``ml`` project needs access to the service instances ``QR-ml`` and ``QR-common``.
   -  The ``finance`` project should have access to the service instances ``QR-finance`` and ``QR-common``.

-  We have three users:

   -  Fatima needs access to the ``ml`` project.
   -  Ravi needs access to the ``finance`` project.
   -  Amyra needs access to both projects.

-  We will use access groups without resource groups.
-  Users are defined in IBM Cloud but project assignments are done in an App ID instance.
-  Users should be able to delete jobs.

The steps to implement this setup are:

1. The Cloud administrator creates an App ID instance and ensures that it is linked in the Cloud administrator’s account. The administrator notes the ID provider URL to share it with users.
2. The Cloud administrator creates three service instances: ``QR-ml``, ``QR finance``, and ``QR-common``.
3. The Cloud administrator creates a custom rule that includes the ``quantum-computing.job.delete`` action.
4. The Cloud administrator creates two access groups:

   -  The ``ml`` access group can access ``QR-ml`` and ``QR-common``. This access group needs a dynamic rule for the App ID IDP that accepts users whose ``project`` attribute contains ``ml``.
   -  The ``finance`` access group can access ``QR-finance`` and ``QR-common``. This access group nees a dynamic rule for the App ID IDP that accepts users whose ``project`` attribute contains ``finance``.

5. The ID provider administrator defines the three users in the IBM Cloud user interface.
6. Users log in at least once.
7. The cloud administrator assigns access by adding users to the access groups that give them access to the projects:

   -  Fatima is given access to the ``ml`` project.
   -  Ravi is given access to the ``finance`` project.
   -  Amyra is given access to the ``ml`` and ``finanace`` projects.

8. Users can log in through the ID provider URL, create API keys, and work with their projects’ service instances.

Next steps
----------

For more information, see `additional considerations <considerations-org>`__.

.. |create| image:: images/org-guide-create-appid.png
.. |identity| image:: images/org-guide-idp-reference.png
.. |access| image:: images/org-guide-manage-user.png