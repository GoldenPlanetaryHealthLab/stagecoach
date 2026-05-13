# Customs


We want to have a secure way of knowing whether a user has the correct
permissions to have data delivered to them via globus. This kind of
validation is going to be called “customs”. As a reminder, the
`Stagecoach` class is a handler for delivering data to townspeople, and
works by issuing users a manifest. This manifest is a JSON file that
users fill in with their credentials and desired data from the Frontier
Gold Mine. Once the user returns the manifest, and the `Stagecoach`
recognizes that the user wants access to data via `globus`, `Dataverse`,
or from the Gold Mine, the `Stagecoach` will call the `customs` handler
and pass this information along. The customs handler then validates the
credentials to ensure that the user has the correct permissions to
access the data. This validation process uses the `Globus SDK`,
`Dataverse API`, or a few simple local file permission checks to verify
the credentials against the data provider service. If the credentials
are valid, the customs handler returns a success message, allowing the
`Stagecoach` to proceed with the data delivery. If the credentials are
invalid, the handler returns an error message, and the `Stagecoach` can
inform the user of the issue and prompt them to correct their
credentials in the manifest. This process ensures that only authorized
users can access the data, maintaining the security of The Frontier’s
Gold Mine resources.

## Globus SDK Authentication and Validation

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

``` python
# import yaml
# from pathlib import Path
# from pprint import pprint
# from pyprojroot import here

# manifest = yaml.safe_load(Path(here() / "stagecoach_manifest.yml").read_text())
# pprint(manifest['sources'])
```

In the customs manager, we will have to do two things: authenticate with
the Globus client, and send the actual data. After wrestling with this
for a few tries, and bouncing design ideas off of chatgpt and jupyter
notebooks, I’ve settled on adding a context helper to do the UserApp
creation:

``` python
from globus_sdk import GlobusAppConfig, TransferClient, UserApp, TransferData
from contextlib import contextmanager

@contextmanager
def globus_transfer_client():
    """
    Yield an authenticated Globus transfer client.

    Yields
    ------
    TransferClient
        Transfer client configured for the Frontier Stagecoach app.
    """
    with UserApp(
        "Frontier-Stagecoach",
        client_id="7723dff4-fa63-4639-903b-ba6541e24e98",
        config=GlobusAppConfig(auto_redrive_gares=True),
    ) as app:
        with TransferClient(app=app) as client:
            yield client
```

This will allow us to create transfer clients with the `with` statement,
allowing us to iterate over the items in the Globus request
individually, granting each of them a unique request and clearance:

``` python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Clearance:
    """
    Represent the outcome of a source access check.

    Attributes
    ----------
    source : str
        Source identifier being validated.
    cleared : bool
        Whether access validation succeeded.
    message : str, default=""
        Human-readable summary of the validation result.
    details : dict[str, Any]
        Source-specific metadata captured during validation.
    """
    
    source: str
    cleared: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

def check_globus_clearance(
    globus_info: dict
    ) -> Clearance:
    """
    Validate access to Globus endpoints and requested source paths.

    Parameters
    ----------
    globus_info : dict
        Manifest subsection describing Globus endpoints and staged items.

    Returns
    -------
    Clearance
        Clearance result describing whether Globus access checks passed.
    """
    try:
        with globus_transfer_client() as client:
            client.get_endpoint(globus_info["source_endpoint"])
            client.get_endpoint(globus_info["destination_endpoint"])
            for item in globus_info["items"]:
                client.operation_stat(
                    globus_info["source_endpoint"],
                    path=item["source_path"],
                )

        return Clearance(
            source="02_globus",
            cleared=True, 
            message="Globus clearance passed.",
            details={
                    "source_endpoint": globus_info["source_endpoint"],
                    "destination_endpoint": globus_info["destination_endpoint"],
                    "items_checked": len(globus_info["items"])
                }
            )

    except Exception as exc:
        return Clearance(
            source="02_globus",
            cleared=False,
            message=str(exc),
            details={
                "source_endpoint": globus_info.get("source_endpoint"),
                "destination_endpoint": globus_info.get("destination_endpoint"),
            }
        )
```

If the checks pass, we can move on to building the transfer logic. This
is built mostly on what we learned above:

``` python
def build_globus_transfer(
    manifest: dict,
    clearance: Clearance,
    fix_holylabs: bool = True,
    label: str = "Stagecoach transfer",
    ) -> TransferData:
    """
    Build a Globus transfer request from manifest settings.

    Parameters
    ----------
    globus_info : dict
        Manifest subsection describing Globus endpoints and staged items.
    clearance : Clearance
        Successful clearance result for the same Globus configuration.
    fix_holylabs : bool, default=True
        Whether to apply Holylabs-specific path fix to the transfer (removes redundant LAB segment from paths).
    label: str, optional
        Optional label for the transfer task.

    Returns
    -------
    TransferData
        Transfer request populated with all requested items.

    Raises
    ------
    ValueError
        Raised when ``clearance`` indicates that access checks failed.
    """
    globus_info = manifest.get("sources", {}).get("02_globus", {})

    if not globus_info:
        raise ValueError("Globus information is missing from the manifest.")

    if not clearance.cleared:
        raise ValueError(f"Cannot build transfer: clearance failed with message: {clearance.message}")
    
    transfer = TransferData(
        source_endpoint=globus_info["source_endpoint"],
        destination_endpoint=globus_info["destination_endpoint"],
        label=label,
    )

    for item in globus_info["items"]:
        
        source_path = item["source_path"].replace("/n/holylabs/LABS/", "/n/holylabs/") if fix_holylabs else item["source_path"]
        destination_root = manifest["project"]["input_data_dir"].replace("/n/holylabs/LABS/", "/n/holylabs/") if fix_holylabs else manifest["project"]["input_data_dir"]
        destination_path = Path(destination_root) / "02_globus" / item['name'] / Path(source_path).name
        
        transfer.add_item(
            str(source_path),
            str(destination_path),
            recursive=item.get("recursive", True),
        )

    return transfer
```

Now with that, the customs manager can first check for clearance, and
additionally build the transfer behind the scenes.

## Gold Mine

Accessing the Gold Mine can only be done from FASRC, for now. It will
implement a simple check for whether the user has access to the
specified path. This will reuse the `Clearance` class from earlier:

``` python
import glob
import os
from pathlib import Path

def check_gold_mine_clearance(
    gold_mine_info: dict
    ) -> Clearance:
    """
    Validate readability of requested Gold Mine paths on FASRC.

    Parameters
    ----------
    gold_mine_info : dict
        Manifest subsection describing Gold Mine staging items.

    Returns
    -------
    Clearance
        Clearance result describing whether all required paths were found
        and were readable.
    """

    try:
        items = gold_mine_info.get("items", [])
        checked = []

        for item in items:
            name = item.get("name", "unnamed")
            path_regex = item.get("path_regex")

            if not path_regex:
                return Clearance(
                    source="01_gold_mine",
                    cleared=False,
                    message=f"{name}: missing path_regex",
                )

            matches = [Path(p) for p in glob.glob(path_regex)]

            if not matches and item.get("required", True):
                return Clearance(
                    source="01_gold_mine",
                    cleared=False,
                    message=f"{name}: no matches for {path_regex}",
                )

            for match in matches:
                if not os.access(match, os.R_OK):
                    return Clearance(
                        source="01_gold_mine",
                        cleared=False,
                        message=f"{name}: path is not readable: {match}",
                    )

            checked.append(
                {
                    "name": name,
                    "path_regex": path_regex,
                    "matches": [str(p) for p in matches],
                }
            )

        return Clearance(
            source="01_gold_mine",
            cleared=True,
            message="Gold Mine clearance passed.",
            details={"items_checked": checked},
        )

    except Exception as exc:
        return Clearance(
            source="01_gold_mine",
            cleared=False,
            message=str(exc),
        )
```

## Dataverse

🚧 Not yet implemented 🚧

## Conclusion

When that sends back a clearance object with `cleared=True`, the
`Stagecoach` can proceed with the transfer using the provided
`transfer_client`. If `cleared=False`, the `Stagecoach` can inform the
user of the issue and prompt them to correct their credentials in the
manifest.

# Script file

The code for this document can be found here:

- [../src/stagecoach/customs.py](../src/stagecoach/customs.py)
