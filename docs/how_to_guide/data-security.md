---

copyright:
  years: 2020, 2021
lastupdated: "2021-10-20"

keywords: data encryption in Qiskit Runtime, data storage for Qiskit Runtime, personal data in Qiskit Runtime, data deletion for Qiskit Runtime, data in Qiskit Runtime, data security in Qiskit Runtime,

subcollection: quantum-computing

---

{{site.data.keyword.attribute-definition-list}}

# Securing your data in Qiskit Runtime
{: #mng-data}

<!-- The title of your H1 should be Securing your data in Qiskit Runtime, where Qiskit Runtime is the non-trademarked short version keyref, but the trademarked version is used in the first occurrence in this topic. Include your service name as a search keyword at the top of your Markdown file. See the example keywords above. -->

To ensure that you can securely manage your data when you use Qiskit Runtime, it is important to know exactly what data is stored and encrypted and how you can delete any stored data.
{: shortdesc}

<!-- Work with your offering's SMEs to fill out the following sections as applicable to your offering. -->

## Protecting your sensitive data in Qiskit Runtime
{: #data-encryption}

The data that you store in {{site.data.keyword.cloud_notm}} is encrypted at rest by using a randomly generated key.

<!-- Some other examples that support both Key Protect and Hyper Protect Crypto Services:
Event Streams: https://test.cloud.ibm.com/docs/EventStreams?topic=EventStreams-managing_encryption
https://test.cloud.ibm.com/docs/appid?topic=appid-mng-data -->


## Deleting your data in Qiskit Runtime
{: #data-delete}

Deleting a service instance removes all of the content associated with that instance, such as your jobs, results, parameters, and programs. To delete an instance, from the [Instances page](https://cloud.ibm.com/quantum/instances), find the instance you want to remove, click its overflow menu, then click **Delete**. You will be asked to confirm the deletion.

### Deleting Qiskit Runtime instances
{: #service-delete}

The Qiskit Runtime data retention policy describes how long your data is stored after you delete the service. The data retention policy is included in the Qiskit Runtime service description, which you can find in the [{{site.data.keyword.cloud_notm}} Terms](https://www.ibm.com/support/customer/csol/terms?id=i126-9425&lc=en#detail-document){: external}.
