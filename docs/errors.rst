.. _errors:

###############
API error codes
###############

.. contents:: Error codes
   :local:

1XXX
====
.. _error1xxx:

.. list-table::
  :header-rows: 1

  * - Error code
    - Message
    - Solution

  * - .. _error1000:

      **1000**
    - API Internal error.
    - Try the action again. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`_ for help.

  * - .. _error1001:

      **1001**
    - qObject is larger than the maximum size.
    - Run a small Job. Split the circuits in smaller jobs.

  * - .. _error1002:

      **1002**
    - Error in the validation process of the job.
    - Check the Job, it is not valid to run on this backend.

  * - .. _error1003:

      **1003**
    - Error in transpilation process.
    - Check the Job, it is not valid to run on this backend.

  * - .. _error1004:

      **1004**
    - The backend is not available.
    - Use another backend to run the job.

  * - .. _error1005:

      **1005**
    - Basis gates not available.
    - Use another backend with basis gates.


  * - .. _error1006:

      **1006**
    - Error during call to converter microservice.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error1007:

      **1007**
    - Backend not found.
    - Check the backend name, maybe it is wrong.

  * - .. _error1008:

      **1008**
    - Error during the validation process of a job.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error1009:

      **1009**
    - Required backend information not found.
    - Use another backend to run the job.

  * - .. _error1010:

      **1010**
    - Error returned at backend level.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error1011:

      **1011**
    - Error publishing job at the backend queue.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error1012:

      **1012**
    - The user reached the maximum number of jobs running concurrently.
    - Wait until some previous jobs were finished. You can cancel pending jobs to run new jobs.

  * - .. _error1101:

      **1101**
    - Qobj does not conform to the schema.
    - Verify the Qobj for your job conforms to the Qobj schema.

  * - .. _error1102:

      **1102**
    - The number of experiments in the Qobj is higher than the number of experiments supported by the backend.
    - Split the experiments into multiple jobs. The maximum number of experiments the backend supports can be found in its configuration data.

  * - .. _error1103:

      **1103**
    - The number of shots in the Qobj is higher than the number of shots supported by the backend.
    - Use fewer shots. The maximum number of shots the backend supports can be found in its configuration data.

  * - .. _error1104:

      **1104**
    - The Qobj requests memory measurement, but the backend does not support memory.
    - Run the job on a backend that supports memory or don't request memory measurement. Whether a backend supports memory measurement can be found in its configuration data.

  * - .. _error1105:

      **1105**
    - The number of qubits used in the Qobj is higher than the number of quantum registers defined in the Qobj.
    - Correct your program and try again.


  * - .. _error1106:

      **1106**
    - The Qobj uses gates that are not among the backend's basis gates.
    - Correct your program and try again. Transpiling your program will convert high level gates to basis gates. The basis gates for a backend can be found in its configuration data.

  * - .. _error1107:

      **1107**
    - The Qobj includes an instruction that assumes a coupling map that is different from the backend's coupling map.
    - Correct your program and try again. Transpiling your program will map instructions to the correct qubits based on the backend's coupling map. The coupling map for a backend can be found in its configuration data.

  * - .. _error1108:

      **1108**
    - The backend does not support open pulse.
    - Run the job on a backend that supports open pulse. Whether a backend supports open pulse can be found in its configuration data.

  * - .. _error1109:

      **1109**
    - The number of qubits used in the Qobj is more than the number of qubits supported by the backend.
    - Run the job on a backend that supports sufficient number of qubits for the job. The number of qubits a backend supports can be found in its configuration data.

  * - .. _error1999:

      **1999**
    - Planned outage. The service is undergoing maintenance.
    - Please wait. The service will be back up soon. The website portal will have more information about what the expected time window for the maintenance work is.


2XXX
====
.. _error2xxx:

.. list-table::
  :header-rows: 1

  * - Error code
    - Message
    - Solution

  * - .. _error2000:

      **2000**
    - Backend not found.
    - Check the backend name, maybe it is wrong.

  * - .. _error2001:

      **2001**
    - Backend not available for booking.
    - Use another backend to book a time slot.

  * - .. _error2002:

      **2002**
    - Backend not available for this action.
    - Use another backend.

  * - .. _error2100:

      **2100**
    - Invalid URL to Upload to Bluemix.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error2200:

      **2200**
    - A booking already exists.
    - Select another date to book.

  * - .. _error2201:

      **2201**
    - Booking data is not valid.
    - Check the booking data, maybe it is wrong.


  * - .. _error2202:

      **2202**
    - Cannot cancel booking.
    - Check the booking to cancel.

  * - .. _error2203:

      **2203**
    - Provider does not have enough remaining time to book.
    - Use another provider to book or contact your Group Administrator.

  * - .. _error2204:

      **2204**
    - User already has a booking on that date.
    - Select another date to book.

  * - .. _error2205:

      **2205**
    - Booking not found.
    - Check the booking data, maybe it is wrong.

  * - .. _error2206:

      **2206**
    - Booking on calibration time.
    - Select another date to book.

  * - .. _error2300:

      **2300**
    - Code ID not found.
    - Check the code data, maybe it is wrong.

  * - .. _error2301:

      **2301**
    - Code not updated.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error2302:

      **2302**
    - Code wrong.
    - Check the code data, maybe it is wrong.

  * - .. _error2304:

      **2304**
    - Error parsing QASM.
    - Check the code data, maybe it is wrong.


  * - .. _error2305:

      **2305**
    - Invalid Code.
    - Check the code data, maybe it is wrong.

  * - .. _error2306:

      **2306**
    - Invalid result.
    - Check the code data, maybe it is wrong.

  * - .. _error2307:

      **2307**
    - The Qobj requests memory measurement, but the backend does not support memory.
    - Check the code data, maybe it is wrong.

  * - .. _error2308:

      **2308**
    - User role not found.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.


  * - .. _error2309:

      **2309**
    - Code not found.
    - Check the code data, maybe it is wrong.


  * - .. _error2310:

      **2310**
    - Failed to export.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error2311:

      **2311**
    - Image wrong.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error2313:

      **2313**
    - QASM not found.
    - Check the code data, maybe it is wrong.

  * - .. _error2400:

      **2400**
    - Error wrong data received.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error2402:

      **2402**
    - Maximum attempts reached.
    - Reduce the number of concurrent requests.

  * - .. _error2403:

      **2403**
    - Missing data in HTTP request.
    - Check your request to the endpoint.


  * - .. _error2404:

      **2404**
    - Model not found in database.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error2405:

      **2405**
    - Error saving new data.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error2407:

      **2407**
    - Authentication required.
    - Try to log in again.

  * - .. _error2408:

      **2408**
    - Invalid Access Token.
    - Try to log in again.

  * - .. _error2409:

      **2409**
    - Forbidden.
    - You don't have authority to perform the action.

  * - .. _error2410:

      **2410**
    - Service not accessible.
    - You don't have authority to perform the action.

  * - .. _error2411:

      **2411**
    - Operation not available.
    - You don't have authority to perform the action.

  * - .. _error2412:

      **2412**
    - Error retrieving data from database.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error2600:

      **2600**
    - Configuration not available for this system.
    - Try to use another backend.

  * - .. _error2602:

      **2602**
    - System not allowed.
    - Try to use another backend.

  * - .. _error2603:

      **2603**
    - Error getting topology attributes.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.


  * - .. _error2604:

      **2604**
    - Error getting topology queues.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error2609:

      **2609**
    - Properties are empty.
    - Try to use another backend.

  * - .. _error2614:

      **2614**
    - Topology without kind established.
    - Try to use another backend. Contact an IBM Quantum administrator.

  * - .. _error2615:

      **2615**
    - The system is not available.
    - Try to use another backend.

  * - .. _error2616:

      **2616**
    - This system can only be used for running jobs.
    - Try the Jobs API. Try to use another backend.

  * - .. _error2618:

      **2618**
    - Basis gates not available.
    - Try to use another backend.

  * - .. _error2620:

      **2620**
    - System not found.
    - Try to use another backend.

  * - .. _error2622:

      **2622**
    - Properties not found.
    - Try to use another backend.

  * - .. _error2900:

      **2900**
    - An error occur getting the hub.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error2901:

      **2901**
    - Error checking hub or group administrators.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error2902:

      **2902**
    - Error checking systems in the Hub.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error2903:

      **2903**
    - Hub info not found.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.


  * - .. _error2904:

      **2904**
    - Invalid backend to configure for booking.
    - Use another backend.

  * - .. _error2905:

      **2905**
    - Invalid parameters to configure for booking.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error2906:

      **2906**
    - Invalid priority value.
    - Change the priority Value.

  * - .. _error2907:

      **2907**
    - System not available for Hub.
    - Use another backend.

  * - .. _error2908:

      **2908**
    - Error checking user in the Hub.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error2909:

      **2909**
    - Group not found.
    - Use another Group.

  * - .. _error2910:

      **2910**
    - Hub not found.
    - Use another Hub.

  * - .. _error2911:

      **2911**
    - Invalid Hub/Group/Project.
    - Use another provider.

  * - .. _error2912:

      **2912**
    - Invalid mode to configure for booking.
    - Use another mode to book a backend.

  * - .. _error2913:

      **2913**
    - Project not found.
    - Use another project.

  * - .. _error2914:

      **2914**
    - This hub is not allowed to view analytics.
    - Use another hub.

3XXX
====
.. _error3xxx:

.. list-table::
  :header-rows: 1

  * - Error code
    - Message
    - Solution

  * - .. _error3200:

      **3200**
    - Backend not valid.
    - Use another backend.

  * - .. _error3202:

      **3202**
    - Cannot get presigned download url.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3203:

      **3203**
    - Cannot get presigned upload url.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3204:

      **3204**
    - Error during call to converter microservice.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.


  * - .. _error3207:

      **3207**
    - Job access not allowed.
    - Access another job.

  * - .. _error3208:

      **3208**
    - Job not cancelled.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3209:

      **3209**
    - Job not running.
    - Check if the action makes sense.

  * - .. _error3210:

      **3210**
    - Job not saved.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3211:

      **3211**
    - Job not valid.
    - Check the Job sent, maybe it is wrong.

  * - .. _error3212:

      **3212**
    - Job not validated.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3213:

      **3213**
    - Job satus not valid.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3214:

      **3214**
    - Job transition not valid.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3215:

      **3215**
    - Job without code identificator.
    - Check the Job sent, maybe it is wrong.


  * - .. _error3216:

      **3216**
    - Limit not valid.
    - Change the limit sent into the request.

  * - .. _error3218:

      **3218**
    - Number of Shots not allowed.
    - Change the number of shots.

  * - .. _error3220:

      **3220**
    - Payload not valid.
    - Change the body sent into the request. Maybe its format is wrong.

  * - .. _error3224:

      **3224**
    - Q-Object memory not allowed.
    - Disable the memory parameter in the Job.


  * - .. _error3226:

      **3226**
    - Q-Object not valid.
    - Check the format of the Job. Maybe it is wrong.


  * - .. _error3228:

      **3228**
    - Q-Object-External-Storage property not allowed in this backend.
    - Send the content of the Job inside of the body.

  * - .. _error3229:

      **3229**
    - QASM no longer accepted.
    - Use Q-Object format.

  * - .. _error3230:

      **3230**
    - Seed not allowed.
    - Don't send seed parameter.

  * - .. _error3233:

      **3233**
    - The job can't be created.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3234:

      **3234**
    - The job can't be validated.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3235:

      **3235**
    - Job cost cannot be calculated.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.


  * - .. _error3236:

      **3236**
    - The job is empty.
    - Check the job sent. Maybe it is empty.

  * - .. _error3237:

      **3237**
    - The job is invalid.
    - Check the job sent. Maybe it is wrong.

  * - .. _error3239:

      **3239**
    - Number of registers exceed the number of qubits.
    - Define the same creg as qreg.

  * - .. _error3242:

      **3242**
    - Circuit count exceeded.
    - Send smaller number of circuits in the Job.

  * - .. _error3243:

      **3243**
    - Circuit is too big.
    - Reduce the content of the circuit.

  * - .. _error3245:

      **3245**
    - The queue is disabled.
    - Use another backend.

  * - .. _error3246:

      **3246**
    - The queue is unavailable.
    - Use another backend.

  * - .. _error3248:

      **3248**
    - Your job is too long.
    - Reduce the content of the job.

  * - .. _error3249:

      **3249**
    - Job fields are empty.
    - Check the Job content. Maybe it is empty.

  * - .. _error3250:

      **3250**
    - Job not found.
    - Check the job ID to query. It is wrong.

  * - .. _error3251:

      **3251**
    - Job not uploaded to object storage.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.


  * - .. _error3252:

      **3252**
    - Object storage not allowed.
    - Send the job into the body of the request.

  * - .. _error3253:

      **3253**
    - Timeout getting the result.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3254:

      **3254**
    - The job is not in queue.
    - Check the status of the job.

  * - .. _error3255:

      **3255**
    - Invalid share level.
    - Update the share level.

  * - .. _error3259:

      **3259**
    - This system can only be used for running jobs.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3265:

      **3265**
    - Input type not allowed by backend.
    - Use another backend.

  * - .. _error3300:

      **3300**
    - Cannot download job data.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3301:

      **3301**
    - Cannot upload job data.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3302:

      **3302**
    - Job not found.
    - Check the job information. Maybe it is wrong.

  * - .. _error3400:

      **3400**
    - License not found.
    - Accept the license.

  * - .. _error3402:

      **3402**
    - API key not found.
    - Regenerate the API Token.

  * - .. _error3405:

      **3405**
    - Codes not deleted.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.


  * - .. _error3407:

      **3407**
    - User API token not valid.
    - Check the API Token.

  * - .. _error3409:

      **3409**
    - Error deleting entities from user.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3410:

      **3410**
    - Error deleting user relations.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3418:

      **3418**
    - Failed to create the token for the user.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3422:

      **3422**
    -  Old password is incorrect.
    - Check your old password. It is wrong.

  * - .. _error3423:

      **3423**
    - Passwords do not match.
    - Check the password. It is wrong.

  * - .. _error3424:

      **3424**
    - Retrieving last version licenses, including future ones.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3425:

      **3425**
    - Retrieving last version licenses.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3440:

      **3440**
    - Authentication is required to perform that action.
    - Try to log in again.

  * - .. _error3443:

      **3443**
    - Failed to check login.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3444:

      **3444**
    - License required. You need to accept the License.
    - Accept the license.

  * - .. _error3445:

      **3445**
    - Login with IBM ID required.
    - Login using IBM ID.

  * - .. _error3446:

      **3446**
    - Login failed.
    - Try to login again.


  * - .. _error3452:

      **3452**
    - The license is not accepted.
    - Accept the License.

  * - .. _error3453:

      **3453**
    - The license is required.
    - Accept the License.

  * - .. _error3458:

      **3458**
    - User reached the maximum limits of concurrent jobs.
    - Wait until some previous jobs were finished. You can cancel pending jobs to run new jobs.

  * - .. _error3459:

      **3459**
    - User is blocked by wrong password.
    - Wait 5 minutes, then log in again.

  * - .. _error3460:

      **3460**
    - User is blocked.
    - Contact an IBM Quantum Administrator.

  * - .. _error3467:

      **3467**
    - Failed to create or renew API token.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3468:

      **3468**
    - Failed to get API token.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3500:

      **3500**
    - Body is wrong.
    - Check the body of the request.

  * - .. _error3704:

      **3704**
    - Error getting status from the queue.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3811:

      **3811**
    - Request not found.
    - Check the request that you are trying to perform.

  * - .. _error3900:

      **3900**
    - Empty response from the stats micro-service.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3901:

      **3901**
    - Error parsing stats.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3902:

      **3902**
    - Error retrieving stats.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3903:

      **3903**
    - Invalid date.
    - Update the dates.

  * - .. _error3904:

      **3904**
    - Invalid end date.
    - Update the end date.

  * - .. _error3905:

      **3905**
    - Invalid input to the stats micro-service.
    - Check the query. It is incorrect.

  * - .. _error3906:

      **3906**
    - Invalid key.
    - Check the query. It is incorrect.

  * - .. _error3907:

      **3907**
    - Invalid start date.
    - Update the start date.

  * - .. _error3908:

      **3908**
    - Invalid stats type.
    - Check the query. It is incorrect.

  * - .. _error3909:

      **3909**
    - Missing mandatory user stats info.
    - Check the query. It is incorrect.

  * - .. _error3910:

      **3910**
    - Number of months too big.
    - Reduce the number of months.

  * - .. _error3911:

      **3911**
    - Stats micro-service is not available.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3912:

      **3912**
    - Stats not found.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3913:

      **3913**
    - Analytics stats not found.
    - Retry the action. If it happens again, contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.

  * - .. _error3914:

      **3914**
    - Project level does not support aggregated analytics stats.
    - Try to use another project.

  * - .. _error3915:

      **3915**
    - Missing start/end dates; allTime not set to true for analytics stats.
    - Set start and end date in the query.

4XXX
====
.. _error4xxx:

.. list-table::
  :header-rows: 1

  * - Error code
    - Message
    - Solution

  * - .. _error4001:

      **4001**
    - Job is part of a session that's been closed
    - Ensure session is not closed before all jobs in session have run

5XXX
====
.. _error5xxx:

.. list-table::
  :header-rows: 1

  * - Error code
    - Message
    - Solution

  * - .. _error5201:

      **5201**
    - Job timed out after {} seconds.
    - Reduce the complexity of the job, or number of shots.

  * - .. _error5202:

      **5202**
    - Job was canceled.
    - None. Job was canceled.

  * - .. _error5203:

      **5203**
    - Failed to run job.
    - Try to run the job again.

  * - .. _error5204:

      **5204**
    - Error raised when execution on AER failed.
    - Try to run the job again.


6XXX
====
.. _error6xxx:

.. list-table::
  :header-rows: 1

  * - Error code
    - Message
    - Solution

  * - .. _error6000:

      **6000**
    - Too many shots given ({} > {}).
    - Reduce the requested number of shots.

  * - .. _error6001:

      **6001**
    - Too few shots given ({} < {}).
    - Increase the requested number of shots.

  * - .. _error6002:

      **6002**
    - Too many experiments given ({} > {}).
    - Reduce the number of experiments.

  * - .. _error6003:

      **6003**
    - Too few experiments given ({} < {}).
    - Increase the number of experiments.


7XXX
====
.. _error7xxx:

.. list-table::
  :header-rows: 1

  * - Error code
    - Message
    - Solution

  * - .. _error7000:

      **7000**
    - Instruction not in basis gates:<br>instruction: {}, qubits: {}, params: {}
    - Instruction not supported by backend. Remove the instruction shown in the error message.

  * - .. _error7001:

      **7001**
    - Instruction {} is not supported.
    - Remove unsupported instruction, or run on a simulator that supports it.

  * - .. _error7002:

      **7002**
    - Memory output is disabled.
    - Select a different backend or set  ``memory=False`` in transpile / execute.

  * - .. _error7003:

      **7003**
    - qubits: {} and classical bits: {} do not have equal lengths.
    - Length of memory slots must be same as number of qubits used.

  * - .. _error7004:

      **7004**
    - Qubit measured multiple times in circuit.
    - Remove multiple measurements on qubits.

  * - .. _error7005:

      **7005**
    - Error in supplied instruction.
    - Refer to the `Operations glossary <../operations_glossary>`__ and verify that the instructions are correct.

  * - .. _error7006:

      **7006**
    - Qubit measurement is followed by instructions.
    - Cannot perform any instruction on a measured qubit. Remove all instructions following a measurement.

8XXX
====
.. _error8xxx:

.. list-table::
  :header-rows: 1

  * - Error code
    - Message
    - Solution

  * - .. _error8000:

      **8000**
    - Channel {}{} lo setting: {} is not within acceptable range of {}.
    - Set channel LO within specified range.

  * - .. _error8001:

      **8001**
    - Qubits {} in measurement are not mapped.
    - Assign qubits to a classical memory slot.

  * - .. _error8002:

      **8002**
    - Total samples exceeds the maximum number of samples for channel {}. ({} > {}).
    - Reduce number of samples below specified limit.

  * - .. _error8003:

      **8003**
    - Total pulses exceeds the maximum number of pulses for channel: {}, ({} > {}).
    - Reduce number of pulses below specified limit.

  * - .. _error8004:

      **8004**
    - Channel {}{} is not available.
    - Must use available drive channels.

  * - .. _error8006:

      **8006**
    - Gate {} in line {}s not understood ({}).
    - This instruction is not supported. Make sure that the gate name is correct and is found within the `Operations glossary <https://quantum-computing.ibm.com/composer/docs/iqx/operations_glossary#operations-glossary>`__.

  * - .. _error8007:

      **8007**
    - Qasm gate not understood: {}.
    - This instruction is not understood. Make sure it is found within the `Operations glossary <https://quantum-computing.ibm.com/composer/docs/iqx/operations_glossary#operations-glossary>`__.

  * - .. _error8008:

      **8008**
    - Unconnected Qubits.
    - Check the topology diagram for this system (go to the `Compute resources page <https://quantum-computing.ibm.com/services/resources?services=systems>`__ and click the system) and make sure the qubits are connected.

  * - .. _error8009:

      **8009**
    - Measurement level is not supported.
    - The given measurement level is not supported on this backend. Change it to 0-2 except the measurement level specified.

  * - .. _error8011:

      **8011**
    - Pulse experiments are not supported on this system.
    - Pulse experiment is not supported on this backend. Use a backend that supports pulse to run this experiment.

  * - .. _error8013:

      **8013**
    - This backend does not support conditional pulses.
    - Conditionals are not supported on this backend. Remove the conditional instruction in your program.

  * - .. _error8014:

      **8014**
    - Reset instructions are not supported.
    - Reset instructions are not supported at this time for this backend. Remove the reset instruction.

  * - .. _error8016:

      **8016**
    - Pulse {} has too few samples ({} > {}).
    - Add more samples.

  * - .. _error8017:

      **8017**
    - Pulse not a multiple of {} samples.
    - Due to hardware limitations, pulses must be a multiple of a given number of samples.

  * - .. _error8018:

      **8018**
    - Waveform memory exceeds the maximum amount of memory currently available.
    - Reduce the number of samples in the waveform.

  * - .. _error8019:

      **8019**
    - For channel {}{}, Final channel time exceeds max time ({} > {}).
    - Reduce the total length of pulse sequence on the specified channel.

  * - .. _error8020:

      **8020**
    - Circuit runtime is greater than the device repetition rate.
    - Circuit too long, reduce length of circuit.


  * - .. _error8021:

      **8021**
    - Acquires have durations of different length.
    - Set acquire operations to have the same length.

  * - .. _error8022:

      **8022**
    - Pulse {} has too many samples ({} > {}).
    - Reduce the number of samples in the specified pulse.

  * - .. _error8023:

      **8023**
    - {0} {1} is an invalid entry. {0} should be a positive integer.
    - Make the entry a positive integer.

  * - .. _error8024:

      **8024**
    - At most one acquire currently supported per acquisition channel.
    - Use only one acquire command per channel.

  * - .. _error8026:

      **8026**
    - Supplied qubits ({0}) in acquire are not valid.
    - Fix the qubits specified in the acquire commands.

  * - .. _error8027:

      **8027**
    - Channel specified: {} is not available.
    - Channel does not exist on system.

  * - .. _error8029:

      **8029**
    - Repetition time ({0}) is not supported.
    - Repetition time must be changed to a supported value.

  * - .. _error8030:

      **8030**
    - Repetition delay ({0}) is not supported.
    - The delay is not supported.


  * - .. _error8031:

      **8031**
    - Submitted job is too long.
    - Reduce the length of the job.

  * - .. _error8033:

      **8033**
    - Qobj ``type`` not provided in ``config``.
    - Add ``type`` to ``qobj['config']``.

  * - .. _error8035:

      **8035**
    - Instruction {0} at timestep {1}dt overlaps with instruction {2} at timestep {3}dt on channel {4}.
    - Two instructions cannot be played at the same time on a channel.

  * - .. _error8036:

      **8036**
    - All measure(circuit) and acquire(pulse) instructions must align to a 16 sample boundary. Measurements may be impacted by delays which have non-multiple of 16 durations.
    - Due to hardware limitations, measure and acquire instructions must occur at 16 sample multiples.

  * - .. _error8037:

      **8037**
    - ESP readout not enabled on this device.
    - Set ``use_measure_esp=False`` or remove from run options.

  * - .. _error8039:

      **8039**
    - A combination of pulses on the logical channels is exceeding the hardware output due to internal usage of hardware output. This will typically be a result of drive and control channels being mapped to the same physical channel in the hardware and the summed total of the applied pulses (including additional internal pulses for system-specific hardware functionality) exceeding unit norm.
    - Lower the amplitudes of the input pulses.

  * - .. _error8041:

      **8041**
    - An amplitude was requested with a norm of greater than 1.
    - Lower the amplitudes of the input pulses.

  * - .. _error8042:

      **8042**
    - The input pulse had some parameters which were not validated. This can be because certain parameters are expected to be real, while others are complex. It may also be due to the amplitude or duration of the pulse exceeding a limit, or other invalid combinations of parameters (e.g., a Gaussian square pulse with a flat-top width greater than the pulse's total duration).
    - Verify the pulse input parameters.

  * - .. _error8044:

      **8044**
    - Number of samples is less than the minimum pulse width.
    - Verify that the duration of all pulses meets or exceeds the minimum pulse duration. If necessary and possible, you may consider zero-padding the start/end of very short pulses such that they meet or exceed the minimum duration.

9XXX
====
.. _error9xxx:

.. list-table::
  :header-rows: 1

  * - Error code
    - Message
    - Solution

  * - .. _error9999:

      **9999**
    - Internal error.
    - Contact IBM Quantum via `Slack <https://ibm.co/joinqiskitslack>`__ for help.
