import uuid
import time
import asyncio
from typing import Literal, Optional, Tuple
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import aioboto3
import app.reports.reporter as reporter


# TODO
# cleanup and reorganize file
# garbage collect tasks after a while
# Make bucket and region configurable

router = APIRouter(prefix="/api/v1")
_task_inventory = {}

# ------------------------------------------------------------------------------
# Report Service
# ------------------------------------------------------------------------------

class ReportSpecArgument(BaseModel):
    name: str = Field(title="Name of the argument")
    short: str = Field(title="Short form description of the argument")
    description: str = Field(title="Description of the argument")
    required: bool = Field(title="Is the argument required")
    type: Literal['cluster', 'timestamp'] = Field(title="Type of the argument")

class ReportSpec(BaseModel):
    id: str = Field(title="Name of the report")
    short: str = Field(title="Short form description of the report")
    description: str = Field(title="Long form description of the report")
    args: list[ReportSpecArgument] = Field(title="List of arguments for the report")

class ReportInventory(BaseModel):
    reports: list[ReportSpec] = Field(title="List of available reports")


@router.get("/report/inventory")
def inventory() -> ReportInventory:
    reports = reporter.get_inventory()
    return ReportInventory.parse_obj(reports)


class ReportInput(BaseModel):
    id: str = Field(title="Id of the report to make")
    args: dict[str, str|float|int|bool] = Field(
        title="A dictionary of name/value pair arguments")
    org_uid: str = Field(
        title="Organization Unique Id to generate the report for")
    api_key: str = Field(
        title="API Key to access the backend data apis for the report")
    api_url: str = Field(
        title="API URL to access the backend data apis for the report")
    mock: dict = Field(
        title="mock json to use to aid in development of the report generation",
        default={})
    format: Optional[Literal["md", "json", "yaml"]] = Field(
        default="md",
        title="Format of the report to generate")

class ReportTaskId(BaseModel):
    id: str = Field(title="Id of the report generation task")

@router.post("/report/make")
def make(
    i: ReportInput,
    background_tasks: BackgroundTasks) -> ReportTaskId:

    # Make identifier for the report generation request
    id = uuid.uuid4().hex

    background_tasks.add_task(schedule_report, id, i)
    return ReportTaskId(id=id)

class ReportTask(BaseModel):
    input: ReportInput = Field(
        title="The input to the report generation")
    s3_uri: str = Field(
        title="The S3 URI where to collect the generated report")
    status: Literal ["scheduled", "failed", "generated", "completed"]=Field(
        title="The status of the report generation")
    error: Optional[str] = Field(
        title="The error message if the report generation failed")
    change_log: list[Tuple[int, dict]] = Field(
        title="The change log of the report generation task")


def register_task(id: str, i: ReportInput, s3_uri: str):
    global _task_inventory
    inv = ReportTask(
        input=i,
        s3_uri=s3_uri,
        status="scheduled",
        error=None,
        change_log=[]
    )
    _task_inventory[id] = inv
    return inv

def get_task(id: str):
    return _task_inventory[id]

def update_task(id: str, **kwargs):
    schedule = get_task(id)
    for k,v in kwargs.items():
        setattr(schedule, k, v)
    schedule.change_log.append((time.time(), kwargs))

async def schedule_report(id: str, i: ReportInput):
    # Register the schedule
    arg_str = "-".join([f"{k}={v}" for k,v in i.args.items()])
    s3_bucket="integration2.reports"
    s3_key=f"reports/{i.org_uid}/{i.id}/{i.format}/{arg_str}"
    s3_uri=f"s3://{s3_bucket}/{s3_key}"
    register_task(id, i, s3_uri)

    # Generate the report
    try:
        report = reporter.make_report(
            report=i.id,
            args=i.args,
            org_uid=i.org_uid,
            api_key=i.api_key,
            api_url=i.api_url,
            mock=i.mock,
            format=i.format
        )
        update_task(id, status="generated")

        # Save the report to S3
        session = aioboto3.Session(region_name="us-east-1", profile_name="integration2")
        async with session.client("s3") as s3:
            await s3.put_object(
                Bucket=s3_bucket,
                Key=s3_key,
                Body=report.encode("utf-8")
            )
        update_task(id, status="completed")
    except Exception as e:
        update_task(id, status="failed")
        update_task(id, error=repr(e))
        import traceback
        traceback.print_exc()


@router.get("/report/status/{id}")
def get_report_status(id: str) -> ReportTask:
    try:
        return get_task(id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Report task id not found")