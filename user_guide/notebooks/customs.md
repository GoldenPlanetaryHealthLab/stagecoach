# Customs


We want to have a secure way of knowing whether a user has the correct
permissions to have data delivered to them via globus. This kind of
validation is going to be called “customs”. As a reminder, the
`Stagecoach` class is a handler for delivering data to townspeople, and
works by issuing users a manifest. This manifest is a JSON file that
users fill in with their credentials and desired data from the Frontier
Gold Mine. Once the user returns the manifest, and the `Stagecoach`
recognizes that the user wants access to data via `globus`, and passes
this information to the customs handler. The customs handler then
validates the credentials to ensure that the user has the correct
permissions to access the data. This validation process uses the
`Globus SDK` to check the credentials against the Globus service. If the
credentials are valid, the customs handler returns a success message,
allowing the `Stagecoach` to proceed with the data delivery. If the
credentials are invalid, the handler returns an error message, and the
`Stagecoach` can inform the user of the issue and prompt them to correct
their credentials in the manifest. This process ensures that only
authorized users can access the data, maintaining the security of The
Frontier’s Gold Mine resources.

## Tinkering with the SDK

Globus SDK in Python works as below. Once you’ve set up an App in the
[Developer
panel](https://globus-sdk-python.readthedocs.io/en/stable/user_guide/getting_started/register_app.html)
of the Globus website, you can use the (non-secure) client UUID to
create a user app:

The first method shows us that login is required to use this app:

Next, we can use this app to define a client group:

What’s great is that this method forces the current user to log in to
their globus account:

![Globus Login](images/groups_client-get-my_g.png)

And from there, I can see the groups I’m allowed to access defined in
the Globus dashboard:

The explicit login can be called deliberately:

We can see that the UserApp object is the main functionality we’re
looking for as it deals solely with the authentication and authorization
of users:

> GlobusApp provides a number of useful abstractions in the SDK. It
> handles login flows and storage of tokens, coupled with later
> retrieval of those tokens for use. It can keep track of which clients
> have been created and registered with an app, and therefore make
> intelligent decisions about how and when to prompt users to login.

So, to make sure someone is logged in, we can simply create a function
that triggers this login flow. Fortunately, Globus has provided an
example we can work with. Let’s take an example of trying to get this
file:

`/n/holylabs/cgolden_lab/Lab/projects/sandbox/ReaProject/MadagascarWeatherStations/_pkgdown.yml`

Let’s list my available data:

The `.get_endpoint()` method is used to get the endpoint information for
a given collection. An important piece of information we’ll need is the
data_access scope of the endpoint, which is a little bit of a
complicated discussion; the tldr I believe is that the transfer client
can be modified to have the correct access scope but only if you check
for it first; hence, the `.get_endpoint()` step. There are two cases
under which the endpoint will NOT have data_access:

1.  If the endpoint `entity_type` IS NOT `GCSv5_mapped_collection`, and
2.  If the endpoint IS `high_assurance`.

If either of the above is true, then the endpoint will need special
access and additional steps. If neither of the above is true, then the
endpoint should be accessible with the default client

So neither of these are true, which means that the endpoint should be
accessible with the default client. If it weren’t the case, we would
have to modify the client with
`tc.add_app_data_access_scope(SRC_COLLECTION)`.

To be sure that this transfer is valid, we can first do a dir_stat on
the collection. If we get a successful response, we can assume that the
transfer will work in future:

Finally, we can wrap the transfer submission in a try-except block to
catch any errors that may arise from invalid credentials or permissions:

That works! So now we can create a validation function that allows the
sheriff to validate the globus section of a stagecoach manifest.

The manifest will have the following shape:

We’ll need to validate that the user has the kind of access necessary.
The return will be a dataclass that the stagecoach can accept the
requisite transfer object from and execute.

``` python
from rich.console import Console
from globus_sdk import GlobusAppConfig, UserApp, TransferClient, GlobusAPIError, TransferData
from dataclasses import dataclass

@dataclass
class GlobusClearance:
    transfer_id : dict | None
    source_collection: str | None
    destination_collection: str | None
    cleared: bool

def issue_globus_transfer(
    globus_info: dict,
    console: Console,
    stagecoach_app_id: str = "7723dff4-fa63-4639-903b-ba6541e24e98",
    issue_transfer: bool = False
    ) -> GlobusClearance:
    """
    Use the Globus SDK to validate globus credentials and optionally issue a transfer.
    Args:
        globus_info (dict): A dictionary containing the globus credentials and information.
        console (Console): Rich console object for output messages.
        stagecoach_app_id (str): The Globus application client ID for authentication.
        issue_transfer (bool): Whether to actually issue a transfer after validation. Defaults to False.
    Returns:
        GlobusClearance: A dataclass indicating the validation result and associated objects.
    """
    try:
        
        if not globus_info.get("use_globus", False):
            console.print("Globus access not requested.")
            return GlobusClearance(
                transfer_id = None,
                source_collection = None,
                destination_collection = None,
                cleared = True
            )
        
        app_name = "Frontier-Customs_" + globus_info.get("globus_username", "Globus-Validator")

        with UserApp(
            app_name,
            client_id=stagecoach_app_id,
            config=GlobusAppConfig(auto_redrive_gares=True),
        ) as app:
            with TransferClient(app=app) as client:
                src_collection = globus_info.get("globus_source_endpoint")
                dst_collection = globus_info.get("globus_destination_endpoint")
                src_path = globus_info.get("globus_source_path")
                dst_path = globus_info.get("globus_destination_path")

                client.add_app_data_access_scope(src_collection)
                client.add_app_data_access_scope(dst_collection)
                
                transfer_request = TransferData(src_collection, dst_collection)
                transfer_request.add_item(src_path, dst_path)
                
                # Attempt to stat the source collection to validate access
                resp = client.operation_stat(src_collection, src_path)
                if resp.http_status == 200:
                    console.print("✅ Globus credentials validated successfully.")
                else:
                    console.print(f"❌ Failed to validate globus credentials. Operation stat returned status: {resp.http_status}")
                    raise GlobusAPIError(resp)

                if issue_transfer:
                    task = client.submit_transfer(transfer_request)
                    console.print(f"Submitted transfer. Task ID: {task['task_id']}.")
                    return GlobusClearance(
                        transfer_id = task,
                        source_collection = src_collection,
                        destination_collection = dst_collection,
                        cleared = True
                    )
                else:
                    return GlobusClearance(
                        transfer_id = None,
                        source_collection = src_collection,
                        destination_collection = dst_collection,
                        cleared = True
                    )

    except GlobusAPIError as e:
        console.print_exception()
        return GlobusClearance(
            transfer_id = None,
            source_collection = globus_info.get("globus_source_endpoint", None),
            destination_collection = globus_info.get("globus_destination_endpoint", None),
            cleared = False
        )  # Return False if there's an API error, along with a clearance object indicating failure
    except Exception as e:
        console.print_exception()
        return GlobusClearance(
            transfer_id = None,
            source_collection = globus_info.get("globus_source_endpoint", None),
            destination_collection = globus_info.get("globus_destination_endpoint", None),
            cleared = False
        )  # Return False for any other unexpected errors, along with a clearance object indicating failure
```

When that sends back a clearance object with `cleared=True`, the
`Stagecoach` can proceed with the transfer using the provided
`transfer_client`. If `cleared=False`, the `Stagecoach` can inform the
user of the issue and prompt them to correct their credentials in the
manifest.

# Script file

The code for this document can be found here:

- [../src/stagecoach/customs.py](../src/stagecoach/customs.py)
