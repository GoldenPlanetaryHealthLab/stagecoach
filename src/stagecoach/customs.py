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
